import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.zenity import ZenityBackend

MODULE = "sampletones_application.utils.file_dialogs.zenity"


def _completed(stdout: str) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    return result


class TestZenityBackend:
    def test_save_command_uses_named_filter_and_filename(self) -> None:
        backend = ZenityBackend()
        file_filter = FileFilter(name="Project files", patterns=("*.stp",))
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/home/user/song.stp\n")) as run:
            result = backend.save_file(
                title="Save project",
                initial_directory=Path("/home/user"),
                suggested_name="song.stp",
                file_filter=file_filter,
            )

        command = run.call_args.args[0]
        assert result == Path("/home/user/song.stp")
        assert "--save" in command
        assert command[command.index("--file-filter") + 1] == "Project files (*.stp) | *.stp"
        assert command[command.index("--filename") + 1] == str(Path("/home/user/song.stp"))

    def test_open_command_filter_format(self) -> None:
        backend = ZenityBackend()
        file_filter = FileFilter(name="Audio files", patterns=("*.wav", "*.mp3"))
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/audio/clip.wav\n")) as run:
            backend.open_file(title="Open", initial_directory=Path("/audio"), file_filter=file_filter)

        command = run.call_args.args[0]
        assert command[command.index("--file-filter") + 1] == "Audio files (*.wav *.mp3) | *.wav *.mp3"

    def test_directory_command_uses_directory_flag(self) -> None:
        backend = ZenityBackend()
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/audio/library\n")) as run:
            result = backend.select_directory(title="Choose", initial_directory=Path("/audio"))

        command = run.call_args.args[0]
        assert result == Path("/audio/library")
        assert "--directory" in command
        assert command[command.index("--filename") + 1].endswith(os.sep)

    def test_cancel_returns_none(self) -> None:
        backend = ZenityBackend()
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("")):
            result = backend.open_file(
                title="Open",
                initial_directory=None,
                file_filter=FileFilter(name="", patterns=("*.stp",)),
            )

        assert result is None
