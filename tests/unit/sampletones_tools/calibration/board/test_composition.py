from pathlib import Path, PurePosixPath
from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.calibration.board.clips import InPlaceClips, clip_store
from sampletones_tools.calibration.board.composition import NO_CLIP, compose_page
from sampletones_tools.calibration.board.model import BoardGlyphs, BoardPage
from sampletones_tools.calibration.board.reading import read_runs
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.fingerprint import write_fingerprint
from sampletones_tools.calibration.layout import combination_name
from sampletones_tools.calibration.renders import RenderRecord, recording_path, write_record
from sampletones_tools.web.roles.table import channel_role
from tests.unit.sampletones_tools.calibration.runs import probe_fingerprint, write_renders, write_run

TITLE: Final[str] = "Calibration"
GLYPHS: Final[BoardGlyphs] = BoardGlyphs(header="≈", expanded="▾", collapsed="▸", play="▶")


def page_of(directories: List[Path], output: Path) -> BoardPage:
    runs = read_runs(directories)
    return compose_page(runs, clip_store(runs, output), TITLE, GLYPHS)


class TestOneRun:
    def test_the_variants_become_the_columns_of_one_table(self, run: Path) -> None:
        page = page_of([run], run)

        assert [group.name for group in page.groups] == ["run-a"]
        assert [column.name for column in page.groups[0].columns] == ["cqt-pe1", "fft-pe1"]

    def test_every_sound_reads_across_the_whole_table(self, run: Path) -> None:
        group = page_of([run], run).groups[0]

        assert [row.item for row in group.rows] == ["tone-a", "mix-a", "chord-a"]
        assert all(len(row.cells) == len(group.columns) for row in group.rows)

    def test_every_row_carries_the_family_its_section_heads(self, run: Path) -> None:
        group = page_of([run], run).groups[0]

        assert [row.family for row in group.rows] == ["sines", "composites", "composites"]

    def test_an_unlisted_sound_stays_off_the_page(self, run: Path) -> None:
        for variant in ("cqt-pe1", "fft-pe1"):
            write_record(
                run,
                RenderRecord(
                    variant=variant,
                    item="note-a",
                    position=3,
                    family="notes",
                    category="notes-pulse",
                    listed=False,
                    timelines={"pulse1": "11"},
                    judgments={"mr-auditory-dB": {"score": 1.0}},
                    silence={"mr-auditory-dB": 20.0},
                ),
            )

        group = page_of([run], run).groups[0]

        assert "note-a" not in [row.item for row in group.rows]

    def test_the_columns_follow_the_order_the_run_measured_its_variants_in(self, tmp_path: Path) -> None:
        run = write_run(tmp_path / "run", ["fft-pe1", "cqt-pe1"], 0.0)

        assert [column.name for column in page_of([run], run).groups[0].columns] == ["fft-pe1", "cqt-pe1"]

    def test_a_row_of_one_level_offers_the_recording_its_cells_reconstruct(self, run: Path) -> None:
        row = page_of([run], run).groups[0].rows[0]

        assert [recording.level for recording in row.recordings] == [VariantLevel.DEFAULT.value]
        assert run / row.recordings[0].clip == recording_path(run, VariantLevel.DEFAULT, row.item)
        assert (run / row.recordings[0].clip).is_file()

    def test_a_row_of_several_levels_offers_the_recording_at_each(self, tmp_path: Path) -> None:
        run = write_renders(tmp_path / "run", ["cqt-pe1"], 0.0, level=VariantLevel.DEFAULT)
        write_renders(run, ["cqt-pe1-true"], 0.0, level=VariantLevel.TRUE)
        write_fingerprint(run, probe_fingerprint(["cqt-pe1", "cqt-pe1-true"]))

        row = page_of([run], run).groups[0].rows[0]

        assert [recording.level for recording in row.recordings] == [level.value for level in VariantLevel]
        assert len({recording.clip for recording in row.recordings}) == len(VariantLevel)
        assert [run / recording.clip for recording in row.recordings] == [
            recording_path(run, level, row.item) for level in VariantLevel
        ]

    def test_a_cell_names_the_render_the_run_wrote(self, run: Path) -> None:
        cell = page_of([run], run).groups[0].rows[0].cells[0]

        assert cell.render == "renders/cqt-pe1/tone-a.flac"
        assert (run / cell.render).is_file()

    def test_the_referee_and_the_channel_colors_travel_with_the_page(self, run: Path) -> None:
        page = page_of([run], run)

        assert page.referee == "mr-auditory-dB"
        assert page.glyphs == GLYPHS
        assert page.colors == {channel.value: channel_role(channel.value) for channel in ChannelName}


class TestHeadings:
    def test_a_group_states_the_words_its_columns_share_once(self, tmp_path: Path) -> None:
        run = write_run(tmp_path / "run", ["cqt-pe1", "cqt-pe1-joint"], 0.0)

        group = page_of([run], run).groups[0]

        assert group.prefix == "cqt-pe1"
        assert [column.words for column in group.columns] == [(), ("joint",)]

    def test_columns_sharing_no_words_keep_every_word(self, run: Path) -> None:
        group = page_of([run], run).groups[0]

        assert group.prefix == ""
        assert [column.words for column in group.columns] == [("cqt", "pe1"), ("fft", "pe1")]


class TestFamilies:
    def test_a_family_per_name_in_the_order_the_rows_first_name_them(self, run: Path) -> None:
        group = page_of([run], run).groups[0]

        assert [family.name for family in group.families] == ["sines", "composites"]

    def test_a_family_holds_every_channel_its_renders_sound_in_the_order_the_hardware_holds_them(
        self, run: Path
    ) -> None:
        group = page_of([run], run).groups[0]

        assert [family.channels for family in group.families] == [
            (ChannelName.TRIANGLE.value,),
            (ChannelName.PULSE1.value, ChannelName.TRIANGLE.value, ChannelName.NOISE.value),
        ]


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
        assert all([column.name for column in group.columns] == ["before", "after"] for group in page.groups)

    def test_a_row_holds_one_cell_per_run(self, runs: List[Path], tmp_path: Path) -> None:
        group = page_of(runs, tmp_path / "page").groups[0]

        assert [cell.score for cell in group.rows[0].cells] == [10.0, 9.0]

    def test_a_row_carries_the_recording_of_the_first_run_holding_it(self, runs: List[Path], tmp_path: Path) -> None:
        output = tmp_path / "page"
        row = page_of(runs, output).groups[0].rows[0]

        (recording,) = row.recordings
        assert (output / recording.clip).is_file()
        assert runs[0].name in PurePosixPath(recording.clip).parts


class TestNoRun:
    def test_a_page_without_a_run_is_refused(self) -> None:
        with pytest.raises(ValueError, match="at least one run"):
            compose_page([], InPlaceClips(), TITLE, GLYPHS)
