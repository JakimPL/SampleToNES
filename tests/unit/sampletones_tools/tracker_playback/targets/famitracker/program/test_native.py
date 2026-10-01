import os
from pathlib import Path

from sampletones_tools.tracker_playback.targets.famitracker.program.native import NativeProgram
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import EXPORT_SWITCH


class TestNativeProgram:
    def test_famitracker_is_handed_every_path_absolute(self, tmp_path: Path) -> None:
        program = NativeProgram(executable=tmp_path / "FamiTracker.exe")

        command = program.export_command(Path("song.ftm"), Path("song.nsf"), Path("song.log"))

        assert command[2] == EXPORT_SWITCH
        assert all(Path(argument).is_absolute() for index, argument in enumerate(command) if index != 2)

    def test_the_export_runs_in_the_checks_own_environment(self, tmp_path: Path) -> None:
        assert NativeProgram(executable=tmp_path / "FamiTracker.exe").environment() == dict(os.environ)
