from pathlib import Path
from typing import List, Optional, Tuple
from unittest.mock import patch

from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
    select_directory_dialog,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter

MODULE = "sampletones_application.utils.file_dialogs.api"

Call = Tuple[str, str, Optional[Path], Optional[FileFilter]]


class FakeBackend:
    def __init__(self, result: Optional[Path]) -> None:
        self._result = result
        self.calls: List[Call] = []

    def open_file(
        self, *, title: str, initial_directory: Optional[Path], file_filter: Optional[FileFilter]
    ) -> Optional[Path]:
        self.calls.append(("open", title, initial_directory, file_filter))
        return self._result

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        self.calls.append(("save", title, initial_directory, file_filter))
        return self._result

    def select_directory(self, *, title: str, initial_directory: Optional[Path]) -> Optional[Path]:
        self.calls.append(("directory", title, initial_directory, None))
        return self._result


class TestSaveFileDialog:
    def test_appends_missing_extension(self) -> None:
        backend = FakeBackend(Path("/home/user/song"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", extensions=[".stp"], filter_name="Project files")

        assert result == Path("/home/user/song.stp")
        file_filter = backend.calls[0][3]
        assert file_filter == FileFilter(name="Project files", patterns=("*.stp",))

    def test_keeps_present_extension(self) -> None:
        backend = FakeBackend(Path("/home/user/song.stp"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", extensions=[".stp"])

        assert result == Path("/home/user/song.stp")

    def test_cancel_returns_none(self) -> None:
        backend = FakeBackend(None)
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", extensions=[".stp"])

        assert result is None

    def test_without_extension_no_filter_and_no_append(self) -> None:
        backend = FakeBackend(Path("/home/user/song"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save")

        assert result == Path("/home/user/song")
        assert backend.calls[0][3] is None


class TestOpenFileDialog:
    def test_builds_filter_and_converts_directory(self) -> None:
        backend = FakeBackend(Path("/audio/clip.wav"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = open_file_dialog(
                title="Open",
                initial_directory="/audio",
                extensions=[".wav", ".mp3"],
                filter_name="Audio files",
            )

        assert result == Path("/audio/clip.wav")
        _, _, initial_directory, file_filter = backend.calls[0]
        assert initial_directory == Path("/audio")
        assert file_filter == FileFilter(name="Audio files", patterns=("*.wav", "*.mp3"))


class TestSelectDirectoryDialog:
    def test_passes_through(self) -> None:
        backend = FakeBackend(Path("/audio/library"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = select_directory_dialog(title="Choose", initial_directory="/audio")

        assert result == Path("/audio/library")
        assert backend.calls[0] == ("directory", "Choose", Path("/audio"), None)
