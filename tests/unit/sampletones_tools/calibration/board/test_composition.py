from pathlib import Path
from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.board.clips import InPlaceClips, clip_store
from sampletones_tools.calibration.board.composition import NO_CLIP, compose_page
from sampletones_tools.calibration.board.model import BoardPage
from sampletones_tools.calibration.board.reading import read_runs
from sampletones_tools.calibration.layout import combination_name

TITLE: Final[str] = "Calibration"


def page_of(directories: List[Path], output: Path) -> BoardPage:
    runs = read_runs(directories)
    return compose_page(runs, clip_store(runs, output), TITLE)


class TestOneRun:
    def test_the_variants_become_the_columns_of_one_table(self, run: Path) -> None:
        page = page_of([run], run)

        assert [group.name for group in page.groups] == ["run-a"]
        assert page.groups[0].columns == ("cqt-pe1", "fft-pe1")

    def test_every_sound_reads_across_the_whole_table(self, run: Path) -> None:
        group = page_of([run], run).groups[0]

        assert [row.item for row in group.rows] == ["tone-a", "mix-a", "chord-a"]
        assert all(len(row.cells) == len(group.columns) for row in group.rows)

    def test_a_cell_names_the_render_the_run_wrote(self, run: Path) -> None:
        cell = page_of([run], run).groups[0].rows[0].cells[0]

        assert cell.render == "renders/cqt-pe1/tone-a.flac"
        assert (run / cell.render).is_file()

    def test_the_referee_and_the_channel_colors_travel_with_the_page(self, run: Path) -> None:
        page = page_of([run], run)

        assert page.referee == "mr-auditory-dB"
        assert page.colors == {channel.value: f"channel_{channel.value}" for channel in ChannelName}


class TestChannels:
    def test_a_lone_channel_offers_nothing_to_switch(self, run: Path) -> None:
        cell = page_of([run], run).groups[0].rows[0].cells[0]

        assert [channel.name for channel in cell.channels] == ["triangle"]
        assert cell.channels[0].solo == NO_CLIP
        assert cell.channels[0].mute == NO_CLIP

    def test_a_channel_plays_alone_and_stands_aside(self, run: Path) -> None:
        cell = page_of([run], run).groups[0].rows[2].cells[0]
        noise = next(channel for channel in cell.channels if channel.name == ChannelName.NOISE.value)

        assert noise.solo.endswith(f"{combination_name([ChannelName.NOISE])}.flac")
        assert noise.mute.endswith(f"{combination_name([ChannelName.PULSE1, ChannelName.TRIANGLE])}.flac")
        assert (run / noise.solo).is_file()
        assert (run / noise.mute).is_file()

    def test_the_channels_follow_the_order_the_hardware_holds_them(self, run: Path) -> None:
        cell = page_of([run], run).groups[0].rows[2].cells[0]

        assert [channel.name for channel in cell.channels] == ["pulse1", "triangle", "noise"]


class TestSeveralRuns:
    def test_each_variant_becomes_a_table_of_its_own(self, runs: List[Path], tmp_path: Path) -> None:
        page = page_of(runs, tmp_path / "page")

        assert [group.name for group in page.groups] == ["cqt-pe1", "fft-pe1"]
        assert all(group.columns == ("before", "after") for group in page.groups)

    def test_a_row_holds_one_cell_per_run(self, runs: List[Path], tmp_path: Path) -> None:
        group = page_of(runs, tmp_path / "page").groups[0]

        assert [cell.score for cell in group.rows[0].cells] == [10.0, 9.0]


class TestNoRun:
    def test_a_page_without_a_run_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least one run"):
            compose_page([], InPlaceClips(), TITLE)
