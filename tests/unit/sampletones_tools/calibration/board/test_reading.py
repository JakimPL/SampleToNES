from pathlib import Path
from typing import List

import pytest

from sampletones_tools.calibration.board.reading import read_run, read_runs
from tests.unit.sampletones_tools.calibration.runs import REFEREE, SILENCE_SCORE, write_run


class TestReadRun:
    def test_a_run_reads_back_every_render_it_wrote(self, run: Path) -> None:
        reading = read_run(run, "run-a")

        assert reading.label == "run-a"
        assert reading.directory == run
        assert reading.variants == ("cqt-pe1", "fft-pe1")
        assert len(reading.records) == 6

    def test_the_records_follow_the_order_the_corpus_generates(self, run: Path) -> None:
        reading = read_run(run, "run-a")

        assert [record.position for record in reading.records] == [0, 0, 1, 1, 2, 2]

    def test_the_headline_referee_is_the_one_the_report_leads_with(self, run: Path) -> None:
        reading = read_run(run, "run-a")

        assert reading.referee == REFEREE
        assert reading.silence(reading.records[0]) == SILENCE_SCORE
        assert reading.score(reading.records[0]) == 10.0

    def test_a_directory_without_renders_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="holds no calibration renders"):
            read_run(tmp_path, "empty")


class TestReadRuns:
    def test_each_run_is_called_by_its_directory(self, runs: List[Path]) -> None:
        assert [reading.label for reading in read_runs(runs)] == ["before", "after"]

    def test_a_name_two_runs_share_is_numbered(self, tmp_path: Path) -> None:
        directories = [
            write_run(tmp_path / "left" / "run", ["cqt-pe1"], 0.0),
            write_run(tmp_path / "right" / "run", ["cqt-pe1"], 0.0),
        ]

        assert [reading.label for reading in read_runs(directories)] == ["run", "run (2)"]
