from typing import Final

from sampletones_core.constants.enums import ChannelName
from sampletones_core.timers.utils import get_timer_table
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.separate import channel_planes
from sampletones_player.compression.seeds import phrases_from_project
from sampletones_player.registers.channel import channel_registers
from sampletones_shared.music import Tuning
from tests.suite.performance import make_pulse_reconstruction, project_with_sample

TUNING: Final[Tuning] = Tuning()
ROWS_PER_PATTERN: Final[int] = 8
SOUNDING_TICKS: Final[int] = 5
PLANES_PER_SLICE: Final[int] = 2


class TestTheInstrumentsSeedTheDictionary:
    """A song plays sample slices at rows, so the shapes its planes repeat are the slices."""

    def test_a_sample_offers_both_planes_of_the_channel_it_plays(self) -> None:
        reconstruction = make_pulse_reconstruction(count=SOUNDING_TICKS)
        project, _ = project_with_sample(reconstruction, rows_per_pattern=ROWS_PER_PATTERN)
        assert len(phrases_from_project(project, TUNING)) == PLANES_PER_SLICE

    def test_the_phrases_are_the_planes_the_slice_writes(self) -> None:
        reconstruction = make_pulse_reconstruction(count=SOUNDING_TICKS)
        project, sample = project_with_sample(reconstruction, rows_per_pattern=ROWS_PER_PATTERN)
        registers = channel_registers(
            ChannelName.PULSE1,
            {ChannelName.PULSE1: sample.reconstruction.get_channel_instructions(ChannelName.PULSE1)},
            get_timer_table(TUNING),
        )
        planes = channel_planes(ChannelName.PULSE1, registers, PitchTable.from_tuning(TUNING))
        assert tuple(phrase.body for phrase in phrases_from_project(project, TUNING)) == planes.ordered

    def test_a_project_holding_no_sample_offers_nothing(self) -> None:
        project, _ = project_with_sample(
            make_pulse_reconstruction(count=SOUNDING_TICKS),
            rows_per_pattern=ROWS_PER_PATTERN,
        )
        project.samples.clear()
        assert phrases_from_project(project, TUNING) == ()
