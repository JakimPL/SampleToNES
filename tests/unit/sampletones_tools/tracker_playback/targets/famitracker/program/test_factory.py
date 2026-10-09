from pathlib import Path

import pytest

from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.program import wine
from sampletones_tools.tracker_playback.targets.famitracker.program.factory import located_program
from sampletones_tools.tracker_playback.targets.famitracker.program.native import NativeProgram
from sampletones_tools.tracker_playback.targets.famitracker.program.wine import WineProgram


@pytest.fixture(name="executable")
def executable_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "FamiTracker.exe"
    path.write_bytes(b"MZ")
    return path


class TestLocatedProgram:
    def test_windows_runs_famitracker_directly(self, monkeypatch: pytest.MonkeyPatch, executable: Path) -> None:
        monkeypatch.setattr(System, "current", classmethod(lambda cls: System.WINDOWS))

        assert located_program(executable) == NativeProgram(executable=executable)

    @pytest.mark.parametrize("system", (System.LINUX, System.MACOS))
    def test_linux_and_macos_run_famitracker_through_wine(
        self,
        monkeypatch: pytest.MonkeyPatch,
        executable: Path,
        system: System,
    ) -> None:
        monkeypatch.setattr(System, "current", classmethod(lambda cls: system))
        monkeypatch.setattr(wine, "locate_program", lambda program: Path("/usr/bin") / program)

        assert located_program(executable) == WineProgram(wine=Path("/usr/bin/wine"), executable=executable)

    def test_a_missing_program_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(FamiTrackerError, match="FamiTracker.exe"):
            located_program(tmp_path / "FamiTracker.exe")

    def test_a_launcher_script_is_refused(self, tmp_path: Path) -> None:
        launcher = tmp_path / "famitracker"
        launcher.write_text("#!/bin/bash\nexec wine FamiTracker.exe", encoding="utf-8")

        with pytest.raises(FamiTrackerError, match="FamiTracker.exe itself"):
            located_program(launcher)
