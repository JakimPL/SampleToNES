from typing import Final, FrozenSet, Tuple

import pytest

from sampletones_core.constants.enums import ALL_CHANNELS, ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes
from sampletones_player.compression.planes.symbols import pack_plane
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.registers.channel import channel_registers
from sampletones_player.specification.binary import unsigned_byte
from sampletones_player.specification.planes import PLANES
from sampletones_shared.music import Tuning
from tests.suite.performance import (
    make_pulse_reconstruction,
    project_with_instrument,
    project_with_sample,
)
from tests.suite.player import PLAYER_FULL_VOLUME, PLAYER_REFERENCE_PITCH

TUNING: Final[Tuning] = Tuning()
ROWS_PER_PATTERN: Final[int] = 8
SOUNDING_TICKS: Final[int] = 5
BENDS: Final[Tuple[int, ...]] = (0, 4, -4, 0)


@pytest.fixture
def project() -> Project:
    """A project playing one pulse slice at a row."""
    reconstruction = make_pulse_reconstruction(count=SOUNDING_TICKS)
    built, _ = project_with_sample(reconstruction, rows_per_pattern=ROWS_PER_PATTERN)
    return built


@pytest.fixture
def slice_planes(project: Project) -> Tuple[bytes, ...]:
    """The planes the project's own slice writes on the channel it plays."""
    instructions = project.voices[0].reconstruction.get_channel_instructions(ChannelName.PULSE1)
    registers = channel_registers(
        ChannelName.PULSE1,
        {ChannelName.PULSE1: instructions},
        get_timer_table(TUNING),
    )
    return channel_planes(ChannelName.PULSE1, registers, PitchTable.from_tuning(TUNING))


def _offered(project: Project) -> Tuple[bytes, ...]:
    return tuple(phrase.body for phrase in phrases_from_project(project, TUNING, ALL_CHANNELS))


NO_BOUNDARIES: Final[FrozenSet[int]] = frozenset()


class TestTheInstrumentsSeedTheDictionary:
    """A song plays sample slices at rows, so the shapes its planes repeat are the slices."""

    def test_the_phrases_are_the_planes_the_slice_turns_over(
        self,
        project: Project,
        slice_planes: Tuple[bytes, ...],
    ) -> None:
        turning = tuple(
            pack_plane(plane, PLANES[index].form, boundaries=NO_BOUNDARIES)
            for index, plane in enumerate(slice_planes)
            if len(set(plane)) > 1
        )
        assert _offered(project) == turning

    def test_a_plane_holding_one_value_offers_the_dictionary_nothing(
        self,
        project: Project,
        slice_planes: Tuple[bytes, ...],
    ) -> None:
        """A hold covers such a plane more cheaply than any phrase naming it could."""
        held = tuple(plane for plane in slice_planes if len(set(plane)) == 1)
        assert held
        assert not set(held) & set(_offered(project))

    def test_a_project_holding_no_sample_offers_nothing(self, project: Project) -> None:
        project.voices.clear()
        assert phrases_from_project(project, TUNING, ALL_CHANNELS) == ()

    def test_a_slice_on_a_channel_the_song_leaves_out_offers_nothing(self, project: Project) -> None:
        """The slice plays on a channel the song rests, so no row of the song ever names it."""
        sounding = ALL_CHANNELS - {ChannelName.PULSE1}
        assert _offered(project)
        assert phrases_from_project(project, TUNING, sounding) == ()


class TestABentSliceSeedsItsBend:
    """A slice that bends turns its bend plane over, so the dictionary is offered that shape too."""

    def test_the_bend_a_slice_plays_is_offered(self) -> None:
        instrument = Instrument(
            name="bent",
            envelopes=InstrumentEnvelopes(
                volume=Envelope(items=(PLAYER_FULL_VOLUME,) * len(BENDS)),
                pitch=Envelope(items=BENDS),
            ),
            initial_pitch=PLAYER_REFERENCE_PITCH,
        )
        project = project_with_instrument(instrument, rows_per_pattern=ROWS_PER_PATTERN)

        bend_plane = bytes(unsigned_byte(bend) for bend in BENDS if bend)
        assert bend_plane in _offered(project)
