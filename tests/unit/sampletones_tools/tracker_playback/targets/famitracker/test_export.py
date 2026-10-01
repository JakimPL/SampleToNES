import subprocess
from pathlib import Path
from typing import Any, List

import pytest

from sampletones_tools.tracker_playback.targets.famitracker import export
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.export import NO_LOG, export_nsf, log_text
from tests.unit.sampletones_tools.tracker_playback.targets.famitracker.programs import (
    LOG_TEXT,
    StandInProgram,
    marking_nsf,
)


@pytest.fixture(name="source")
def source_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "prepared.nsf"
    path.write_bytes(marking_nsf())
    return path


class TestExportNSF:
    def test_the_nsf_the_export_writes_is_left_in_place(self, tmp_path: Path, source: Path) -> None:
        program = StandInProgram(executable=tmp_path / "FamiTracker.exe", source=source, exported=[])
        module = tmp_path / "song.ftm"
        module.write_bytes(b"module")

        export_nsf(program, module, tmp_path / "song.nsf", tmp_path / "song.log")

        assert (tmp_path / "song.nsf").read_bytes() == source.read_bytes()
        assert program.exported == [b"module"]

    def test_an_export_writing_no_nsf_is_reported_with_its_log(self, tmp_path: Path) -> None:
        program = StandInProgram(executable=tmp_path / "FamiTracker.exe", source=None, exported=[])
        module = tmp_path / "song.ftm"
        module.write_bytes(b"module")

        with pytest.raises(FamiTrackerError, match="NSF export complete"):
            export_nsf(program, module, tmp_path / "song.nsf", tmp_path / "song.log")

    def test_an_nsf_left_by_an_earlier_run_counts_for_nothing(self, tmp_path: Path) -> None:
        program = StandInProgram(executable=tmp_path / "FamiTracker.exe", source=None, exported=[])
        module = tmp_path / "song.ftm"
        module.write_bytes(b"module")
        (tmp_path / "song.nsf").write_bytes(b"stale")

        with pytest.raises(FamiTrackerError):
            export_nsf(program, module, tmp_path / "song.nsf", tmp_path / "song.log")

        assert not (tmp_path / "song.nsf").exists()

    def test_an_export_running_past_its_time_is_reported(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        def run(*arguments: Any, **options: Any) -> List[str]:
            raise subprocess.TimeoutExpired(cmd="FamiTracker.exe", timeout=options["timeout"])

        monkeypatch.setattr(export.subprocess, "run", run)
        program = StandInProgram(executable=tmp_path / "FamiTracker.exe", source=None, exported=[])
        module = tmp_path / "song.ftm"
        module.write_bytes(b"module")

        with pytest.raises(FamiTrackerError, match="seconds"):
            export_nsf(program, module, tmp_path / "song.nsf", tmp_path / "song.log")


class TestLogText:
    def test_the_log_is_read_as_written(self, tmp_path: Path) -> None:
        (tmp_path / "song.log").write_text(LOG_TEXT, encoding="utf-8")

        assert log_text(tmp_path / "song.log") == LOG_TEXT

    def test_a_missing_log_says_so(self, tmp_path: Path) -> None:
        assert log_text(tmp_path / "song.log") == NO_LOG
