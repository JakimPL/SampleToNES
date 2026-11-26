from pathlib import Path
from typing import List

import pytest

from sampletones_tools.calibration.board.reading import read_run, read_runs
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.fingerprint import FINGERPRINT_FILE, write_fingerprint
from sampletones_tools.calibration.layout import ORACLE_LABEL
from tests.unit.sampletones_tools.calibration.runs import (
    REFEREE,
    SILENCE_SCORE,
    probe_fingerprint,
    write_oracle,
    write_renders,
    write_run,
)


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

    def test_the_oracle_is_read_beside_the_variants_the_run_measured(self, run: Path) -> None:
        write_oracle(run, ["tone-a"])

        reading = read_run(run, "run-a")

        assert reading.holds_oracle
        assert reading.variants == ("cqt-pe1", "fft-pe1")
        assert [record.item for record in reading.records if record.variant == ORACLE_LABEL] == ["tone-a"]

    def test_a_run_holds_no_oracle_until_one_is_read(self, run: Path) -> None:
        assert not read_run(run, "run-a").holds_oracle

    def test_a_directory_without_renders_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="holds no calibration renders"):
            read_run(tmp_path, "empty")

    def test_the_variants_follow_the_order_the_run_measured_them_in(self, tmp_path: Path) -> None:
        run = write_run(tmp_path / "run", ["fft-pe1", "cqt-pe1-greedy", "cqt-pe1"], 0.0)

        assert read_run(run, "run").variants == ("fft-pe1", "cqt-pe1-greedy", "cqt-pe1")

    def test_records_of_a_variant_the_run_never_measured_are_left_unread(self, tmp_path: Path) -> None:
        run = write_run(tmp_path / "run", ["cqt-pe1"], 0.0)
        write_renders(run, ["fft-pe1"], 0.0, level=VariantLevel.DEFAULT)

        reading = read_run(run, "run")

        assert reading.variants == ("cqt-pe1",)
        assert {record.variant for record in reading.records} == {"cqt-pe1"}

    def test_a_variant_the_run_stopped_before_is_left_out(self, tmp_path: Path) -> None:
        run = write_renders(tmp_path / "run", ["fft-pe1"], 0.0, level=VariantLevel.DEFAULT)
        write_fingerprint(run, probe_fingerprint(["fft-pe1", "cqt-pe1"]))

        assert read_run(run, "run").variants == ("fft-pe1",)

    def test_a_run_without_a_fingerprint_is_reported(self, tmp_path: Path) -> None:
        run = write_renders(tmp_path / "run", ["cqt-pe1"], 0.0, level=VariantLevel.DEFAULT)

        with pytest.raises(FileNotFoundError, match=f"holds no {FINGERPRINT_FILE}"):
            read_run(run, "run")


class TestReadRuns:
    def test_each_run_is_called_by_its_directory(self, runs: List[Path]) -> None:
        assert [reading.label for reading in read_runs(runs)] == ["before", "after"]

    def test_a_name_two_runs_share_is_numbered(self, tmp_path: Path) -> None:
        directories = [
            write_run(tmp_path / "left" / "run", ["cqt-pe1"], 0.0),
            write_run(tmp_path / "right" / "run", ["cqt-pe1"], 0.0),
        ]

        assert [reading.label for reading in read_runs(directories)] == ["run", "run (2)"]
