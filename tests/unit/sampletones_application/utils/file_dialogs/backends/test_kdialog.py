from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

from sampletones_application.utils.file_dialogs.backends.kdialog import KDialogBackend
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter

MODULE = "sampletones_application.utils.file_dialogs.backends.kdialog"


def _chosen(path: Optional[Path]) -> AbstractContextManager[MagicMock]:
    """Answers the dialog with ``path``, standing in for what ``kdialog`` reports."""
    return patch(f"{MODULE}.run_dialog_command", return_value=path)


class TestKDialogBackend:
    def test_save_command_carries_suggested_name_and_named_filter(self) -> None:
        backend = KDialogBackend()
        file_filter = FileFilter(name="Project files", patterns=("*.stp",))
        with _chosen(Path("/home/user/song.stp")) as run:
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
        with _chosen(Path("/audio/clip.wav")) as run:
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
        with _chosen(Path("/home/user/kick.json")) as run:
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
        with _chosen(Path("/audio/library")) as run:
            result = backend.select_directory(title="Choose", initial_directory=Path("/audio"))

        command = run.call_args.args[0]
        assert result == Path("/audio/library")
        assert "--getexistingdirectory" in command
        assert not any("|" in part for part in command)

    def test_cancel_returns_none(self) -> None:
        backend = KDialogBackend()
        with _chosen(None):
            result = backend.save_file(
                title="Save",
                initial_directory=None,
                suggested_name=None,
                filters=(FileFilter(name="", patterns=("*.stp",)),),
            )

        assert result is None
