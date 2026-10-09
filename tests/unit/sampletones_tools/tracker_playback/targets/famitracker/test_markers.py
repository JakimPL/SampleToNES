from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.builder import build_module
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.specification.channels import ChannelId
from sampletones_core.formats.famitracker.specification.patterns import MAX_DAC_LEVEL, EffectId
from sampletones_core.project.settings import ProjectSettings
from sampletones_tools.tracker_playback.targets.famitracker.markers import MARKER_LEVELS, marked_module, row_marker
from tests.suite.performance import make_pulse_reconstruction, place_instrument, project_with_sample

ROWS: Final[int] = 4
FRAMES: Final[int] = 3


@pytest.fixture(name="module")
def module_fixture() -> FamiTrackerModule:
    """A module of three frames of four rows, a note on pulse 1 in the first."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=4),
        rows_per_pattern=ROWS,
        settings=ProjectSettings(tempo=150, speed=6, nes_frequency=60),
    )
    place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=sample, volume=15)
    project.song.order.extend(dict(project.song.order[0]) for _ in range(FRAMES - 1))
    return build_module(project).document


class TestRowMarker:
    def test_a_marker_is_the_rows_place_wrapped_into_the_marker_levels(self) -> None:
        last = MARKER_LEVELS - 1

        assert [row_marker(index) for index in (0, 1, last, last + 1)] == [0, 1, last, 0]

    def test_every_marker_is_a_level_the_dmc_takes(self) -> None:
        assert MARKER_LEVELS - 1 <= MAX_DAC_LEVEL

    def test_two_rows_in_a_row_carry_different_markers(self) -> None:
        assert all(row_marker(index) != row_marker(index + 1) for index in range(1000))


class TestMarkedModule:
    def test_every_frame_plays_a_dpcm_pattern_of_its_own(self, module: FamiTrackerModule) -> None:
        marked = marked_module(module)

        assert [entries[ChannelId.DPCM] for entries in marked.track.order] == list(range(FRAMES))

    def test_every_row_loads_its_place_in_the_song(self, module: FamiTrackerModule) -> None:
        marked = marked_module(module)
        levels: List[int] = []
        for frame in range(FRAMES):
            (pattern,) = (
                pattern
                for pattern in marked.track.patterns
                if pattern.channel == ChannelId.DPCM and pattern.index == frame
            )
            levels.extend(level for cell in pattern.rows for effect, level in cell.effects if effect == EffectId.DAC)

        assert levels == [row_marker(index) for index in range(FRAMES * ROWS)]

    def test_the_other_channels_stay_as_the_export_built_them(self, module: FamiTrackerModule) -> None:
        marked = marked_module(module)

        def tonal(document: FamiTrackerModule) -> object:
            return (
                [entries[: ChannelId.DPCM] for entries in document.track.order],
                [pattern for pattern in document.track.patterns if pattern.channel != ChannelId.DPCM],
                document.instruments,
            )

        assert tonal(marked) == tonal(module)
