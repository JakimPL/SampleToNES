from pathlib import Path
from unittest.mock import MagicMock, patch

from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.kdialog import KDialogBackend

MODULE = "sampletones_application.utils.file_dialogs.kdialog"


def _completed(stdout: str) -> MagicMock:
    result = MagicMock()
    result.stdout = stdout
    return result


class TestKDialogBackend:
    def test_save_command_carries_suggested_name_and_named_filter(self) -> None:
        backend = KDialogBackend()
        file_filter = FileFilter(name="Project files", patterns=("*.stp",))
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/home/user/song.stp\n")) as run:
            result = backend.save_file(
                title="Save project",
                initial_directory=Path("/home/user"),
                suggested_name="song.stp",
                filters=(file_filter,),
            )

        command = run.call_args.args[0]
        assert result == SaveDestination(path=Path("/home/user/song.stp"), file_type=None)
        assert "--getsavefilename" in command
        assert str(Path("/home/user/song.stp")) in command
        assert "*.stp|Project files (*.stp)" in command
        assert command[command.index("--title") + 1] == "Save project"

    def test_open_command_carries_multi_pattern_filter(self) -> None:
        backend = KDialogBackend()
        file_filter = FileFilter(name="Audio files", patterns=("*.wav", "*.mp3"))
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/audio/clip.wav\n")) as run:
            result = backend.open_file(
                title="Open",
                initial_directory=Path("/audio"),
                filters=(file_filter,),
            )

        command = run.call_args.args[0]
        assert result == Path("/audio/clip.wav")
        assert "--getopenfilename" in command
        assert "*.wav *.mp3|Audio files (*.wav *.mp3)" in command

    def test_several_types_gather_into_one_filter_naming_each(self) -> None:
        """One filter reaches ``kdialog``'s command line, so it carries every accepted
        pattern behind a label naming each type.
        """
        backend = KDialogBackend()
        filters = (
            FileFilter(name="FamiTracker instrument", patterns=("*.fti",)),
            FileFilter(name="Bitphase preset", patterns=("*.json",)),
        )
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/home/user/kick.json\n")) as run:
            backend.save_file(
                title="Export instrument",
                initial_directory=Path("/home/user"),
                suggested_name="kick",
                filters=filters,
            )

        command = run.call_args.args[0]
        assert "*.fti *.json|FamiTracker instrument, Bitphase preset (*.fti *.json)" in command

    def test_directory_command_has_no_filter(self) -> None:
        backend = KDialogBackend()
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("/audio/library\n")) as run:
            result = backend.select_directory(title="Choose", initial_directory=Path("/audio"))

        command = run.call_args.args[0]
        assert result == Path("/audio/library")
        assert "--getexistingdirectory" in command
        assert not any("|" in part for part in command)

    def test_cancel_returns_none(self) -> None:
        backend = KDialogBackend()
        with patch(f"{MODULE}.subprocess.run", return_value=_completed("")):
            result = backend.save_file(
                title="Save",
                initial_directory=None,
                suggested_name=None,
                filters=(FileFilter(name="", patterns=("*.stp",)),),
            )

        assert result is None
