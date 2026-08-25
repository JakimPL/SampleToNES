from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.project import Project
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.channel import ChannelPlanes
from sampletones_player.compression.planes.separate import channel_planes
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.registers.channel import channel_registers
from sampletones_shared.music import Tuning
from tests.suite.performance import make_pulse_reconstruction, project_with_sample

TUNING: Final[Tuning] = Tuning()
ROWS_PER_PATTERN: Final[int] = 8
SOUNDING_TICKS: Final[int] = 5


@pytest.fixture
def project() -> Project:
    """A project playing one pulse slice at a row."""
    reconstruction = make_pulse_reconstruction(count=SOUNDING_TICKS)
    built, _ = project_with_sample(reconstruction, rows_per_pattern=ROWS_PER_PATTERN)
    return built


@pytest.fixture
def slice_planes(project: Project) -> ChannelPlanes:
    """The planes the project's own slice writes on the channel it plays."""
    instructions = project.voices[0].reconstruction.get_channel_instructions(ChannelName.PULSE1)
    registers = channel_registers(
        ChannelName.PULSE1,
        {ChannelName.PULSE1: instructions},
        get_timer_table(TUNING),
    )
    return channel_planes(ChannelName.PULSE1, registers, PitchTable.from_tuning(TUNING))


def _offered(project: Project) -> Tuple[bytes, ...]:
    return tuple(phrase.body for phrase in phrases_from_project(project, TUNING))


class TestTheInstrumentsSeedTheDictionary:
    """A song plays sample slices at rows, so the shapes its planes repeat are the slices."""

    def test_the_phrases_are_the_planes_the_slice_turns_over(
        self,
        project: Project,
        slice_planes: ChannelPlanes,
    ) -> None:
        turning = tuple(plane for plane in slice_planes.ordered if len(set(plane)) > 1)
        assert _offered(project) == turning

    def test_a_plane_holding_one_value_offers_the_dictionary_nothing(
        self,
        project: Project,
        slice_planes: ChannelPlanes,
    ) -> None:
        """A hold covers such a plane more cheaply than any phrase naming it could."""
        held = tuple(plane for plane in slice_planes.ordered if len(set(plane)) == 1)
        assert held
        assert not set(held) & set(_offered(project))

    def test_a_project_holding_no_sample_offers_nothing(self, project: Project) -> None:
        project.voices.clear()
        assert phrases_from_project(project, TUNING) == ()
