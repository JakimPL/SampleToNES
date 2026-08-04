import os
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

from sampletones_application.utils.file_dialogs.backends.zenity import ZenityBackend
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter

MODULE = "sampletones_application.utils.file_dialogs.backends.zenity"


def _chosen(path: Optional[Path]) -> AbstractContextManager[MagicMock]:
    """Answers the dialog with ``path``, standing in for what ``zenity`` reports."""
    return patch(f"{MODULE}.run_dialog_command", return_value=path)


class TestZenityBackend:
    def test_save_command_uses_named_filter_and_filename(self) -> None:
        backend = ZenityBackend()
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
        assert "--save" in command
        assert command[command.index("--file-filter") + 1] == "Project files (*.stp) | *.stp"
        assert command[command.index("--filename") + 1] == str(Path("/home/user/song.stp"))

    def test_open_command_filter_format(self) -> None:
        backend = ZenityBackend()
        file_filter = FileFilter(name="Audio files", patterns=("*.wav", "*.mp3"))
        with _chosen(Path("/audio/clip.wav")) as run:
            backend.open_file(title="Open", initial_directory=Path("/audio"), filters=(file_filter,))

        command = run.call_args.args[0]
        assert command[command.index("--file-filter") + 1] == "Audio files (*.wav *.mp3) | *.wav *.mp3"

    def test_each_offered_type_reaches_the_selector_as_its_own_entry(self) -> None:
        """GTK narrows the browser by the type picked in the selector, so every accepted
        type is listed for itself.
        """
        backend = ZenityBackend()
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
        assert command.count("--file-filter") == 2
        assert "FamiTracker instrument (*.fti) | *.fti" in command
        assert "Bitphase preset (*.json) | *.json" in command

    def test_directory_command_uses_directory_flag(self) -> None:
        backend = ZenityBackend()
        with _chosen(Path("/audio/library")) as run:
            result = backend.select_directory(title="Choose", initial_directory=Path("/audio"))

        command = run.call_args.args[0]
        assert result == Path("/audio/library")
        assert "--directory" in command
        assert command[command.index("--filename") + 1].endswith(os.sep)

    def test_cancel_returns_none(self) -> None:
        backend = ZenityBackend()
        with _chosen(None):
            result = backend.open_file(
                title="Open",
                initial_directory=None,
                filters=(FileFilter(name="", patterns=("*.stp",)),),
            )

        assert result is None
