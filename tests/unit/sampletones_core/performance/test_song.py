from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.maps import CHANNEL_TO_EXPORTER_MAP
from sampletones_core.performance import WalkProgress, song_instructions
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.timing import SongTiming
from sampletones_shared.exceptions import OperationCanceled
from tests.suite.performance import (
    make_pulse_reconstruction,
    place_instrument,
    project_with_sample,
)

ROWS_PER_PATTERN: Final[int] = 4
ENVELOPE_TICKS: Final[int] = 2
SETTINGS: Final[ProjectSettings] = ProjectSettings(tempo=150, speed=6, nes_frequency=60)


def _project() -> Project:
    """A one-frame project sounding a two-tick pulse envelope from the first row."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=ENVELOPE_TICKS),
        rows_per_pattern=ROWS_PER_PATTERN,
        settings=SETTINGS,
    )
    place_instrument(
        project,
        channel_name=ChannelName.PULSE1,
        row_index=0,
        sample=sample,
    )
    return project


def _resting(channel_name: ChannelName) -> object:
    return CHANNEL_TO_EXPORTER_MAP[channel_name].get_instruction_type().null_instruction()


class TestSongInstructions:
    """The four streams a song plays out as, one instruction per channel per engine tick."""

    def test_the_song_lasts_the_ticks_its_groove_gives_every_row_it_plays(self) -> None:
        project = _project()
        groove = SongTiming.from_project(project).groove()

        streams = song_instructions(project)

        expected_ticks = project.song.order_length() * groove.total_ticks
        assert len(streams[ChannelName.PULSE1]) == expected_ticks

    def test_every_channel_answers_for_every_tick(self) -> None:
        """One length across the four streams is what makes a tick index one moment of the song."""
        streams = song_instructions(_project())

        assert len({len(stream) for stream in streams.values()}) == 1

    def test_a_channel_no_row_names_rests_throughout(self) -> None:
        streams = song_instructions(_project())

        assert streams[ChannelName.TRIANGLE] == [_resting(ChannelName.TRIANGLE)] * len(streams[ChannelName.TRIANGLE])

    def test_a_sounding_channel_falls_silent_once_its_envelope_plays_out(self) -> None:
        """A one-shot sounds for the ticks it carries and rests for the rest of the row."""
        stream = song_instructions(_project())[ChannelName.PULSE1]
        resting = _resting(ChannelName.PULSE1)

        assert stream[:ENVELOPE_TICKS] != [resting] * ENVELOPE_TICKS
        assert stream[ENVELOPE_TICKS:] == [resting] * (len(stream) - ENVELOPE_TICKS)

    def test_a_pattern_the_order_plays_twice_sounds_alike_both_times(self) -> None:
        """The order is where reuse lives, so the ticks a repeated frame produces are the same."""
        project = _project()
        project.song.append_frame()
        project.song.set_order_entry(1, ChannelName.PULSE1, 0)
        groove = SongTiming.from_project(project).groove()

        stream = song_instructions(project)[ChannelName.PULSE1]

        frame_ticks = groove.total_ticks
        assert stream[:frame_ticks] == stream[frame_ticks : 2 * frame_ticks]


class TestWhatAWalkSaysAboutItself:
    """A song of minutes is played out row by row, so the walk says how far along it is."""

    def test_the_walk_reports_each_row_it_sounds(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        assert len(heard) == project.song.order_length() * project.song.rows_per_pattern

    def test_the_walk_states_the_ticks_the_order_lasts(self) -> None:
        """The groove states the length before a row is played, so every report names the same."""
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        expected = project.song.order_length() * SongTiming.from_project(project).groove().total_ticks
        assert [progress.total for progress in heard] == [expected] * len(heard)

    def test_the_walk_reaches_the_ticks_it_set_out_to_sound(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        assert heard[-1].ticks == heard[-1].total

    def test_the_walk_counts_up_as_it_goes(self) -> None:
        project = _project()
        heard: List[WalkProgress] = []
        song_instructions(project, lambda progress: heard.append(progress) is None)
        counted = [progress.ticks for progress in heard]
        assert counted == sorted(counted)

    def test_a_withdrawn_walk_stops_where_it_was_told(self) -> None:
        with pytest.raises(OperationCanceled):
            song_instructions(_project(), lambda progress: False)
