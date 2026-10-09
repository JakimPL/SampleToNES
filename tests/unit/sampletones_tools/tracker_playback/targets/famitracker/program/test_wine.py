import subprocess
from pathlib import Path
from typing import Any, Final, List

import pytest

from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.program import wine
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import EXPORT_SWITCH
from sampletones_tools.tracker_playback.targets.famitracker.program.wine import (
    DISPLAY_VARIABLES,
    INSTALL_HINTS,
    WINE_DEBUG,
    WINE_DEBUG_SILENT,
    WINEPATH,
    WineProgram,
)

WINE: Final[Path] = Path("/usr/bin/wine")
EXECUTABLE: Final[Path] = Path("/apps/FamiTracker.exe")


def on_drive_z(path: str) -> str:
    """A path as a default Wine prefix maps it: the file system's root is drive Z."""
    return "Z:" + path.replace("/", "\\")


class MappingWine:
    """Wine's ``winepath`` standing in: it maps each path onto drive Z and records the commands it ran."""

    def __init__(self) -> None:
        self.commands: List[List[str]] = []

    def run(self, command: List[str], **options: Any) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        mapped = "".join(f"{on_drive_z(path)}\n" for path in command[3:])
        return subprocess.CompletedProcess(command, 0, stdout=mapped, stderr="")


@pytest.fixture(name="mapping")
def mapping_fixture(monkeypatch: pytest.MonkeyPatch) -> MappingWine:
    mapping = MappingWine()
    monkeypatch.setattr(wine.subprocess, "run", mapping.run)
    return mapping


class TestLocating:
    def test_the_program_takes_the_wine_this_system_has(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(wine, "locate_program", lambda program: Path("/opt/bin") / program)

        assert WineProgram.located(EXECUTABLE) == WineProgram(wine=Path("/opt/bin/wine"), executable=EXECUTABLE)

    def test_an_absent_wine_names_how_this_system_installs_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(wine, "locate_program", lambda program: None)
        monkeypatch.setattr(System, "current", classmethod(lambda cls: System.LINUX))

        with pytest.raises(FamiTrackerError, match=INSTALL_HINTS[System.LINUX]):
            WineProgram.located(EXECUTABLE)


class TestTheExportCommand:
    def test_famitracker_is_handed_every_path_as_wine_maps_it(self, mapping: MappingWine, tmp_path: Path) -> None:
        program = WineProgram(wine=WINE, executable=EXECUTABLE)

        module, nsf, log = (tmp_path / name for name in ("song.ftm", "song.nsf", "song.log"))

        command = program.export_command(module, nsf, log)

        assert command == [
            str(WINE),
            str(EXECUTABLE),
            on_drive_z(str(module.resolve())),
            EXPORT_SWITCH,
            on_drive_z(str(nsf.resolve())),
            on_drive_z(str(log.resolve())),
        ]

    def test_wine_maps_every_path_in_one_call(self, mapping: MappingWine, tmp_path: Path) -> None:
        WineProgram(wine=WINE, executable=EXECUTABLE).export_command(tmp_path / "a", tmp_path / "b", tmp_path / "c")

        (command,) = mapping.commands
        assert command[:3] == [str(WINE), WINEPATH, "-w"]

    def test_a_failed_mapping_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def run(command: List[str], **options: Any) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(1, command, stderr="no prefix")

        monkeypatch.setattr(wine.subprocess, "run", run)

        with pytest.raises(FamiTrackerError, match="no prefix"):
            WineProgram(wine=WINE, executable=EXECUTABLE).windows_paths((tmp_path,))

    def test_a_mapping_missing_a_path_is_reported(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def run(command: List[str], **options: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, stdout="Z:\\one\n", stderr="")

        monkeypatch.setattr(wine.subprocess, "run", run)

        with pytest.raises(FamiTrackerError):
            WineProgram(wine=WINE, executable=EXECUTABLE).windows_paths((tmp_path / "a", tmp_path / "b"))


class TestTheEnvironment:
    def test_the_export_runs_with_no_display_and_wine_silenced(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for variable in DISPLAY_VARIABLES:
            monkeypatch.setenv(variable, ":1")

        environment = WineProgram(wine=WINE, executable=EXECUTABLE).environment()

        assert not set(DISPLAY_VARIABLES) & set(environment)
        assert environment[WINE_DEBUG] == WINE_DEBUG_SILENT

    def test_the_rest_of_the_environment_carries_over(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WINEPREFIX", "/home/someone/.wine-famitracker")

        environment = WineProgram(wine=WINE, executable=EXECUTABLE).environment()

        assert environment["WINEPREFIX"] == "/home/someone/.wine-famitracker"
