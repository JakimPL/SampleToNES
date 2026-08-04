from pathlib import Path
from typing import Final, List, Optional, Tuple
from unittest.mock import patch

from sampletones_application.utils.file_dialogs.api import (
    open_file_dialog,
    save_file_dialog,
    select_directory_dialog,
)
from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter

MODULE = "sampletones_application.utils.file_dialogs.api"

PROJECT_FILTER: Final[FileFilter] = FileFilter(name="Project files", patterns=("*.stp",))
FAMITRACKER_FILTER: Final[FileFilter] = FileFilter(name="FamiTracker instrument", patterns=("*.fti",))
PRESET_FILTER: Final[FileFilter] = FileFilter(name="Bitphase preset", patterns=("*.json",))
INSTRUMENT_FILTERS: Final[Tuple[FileFilter, ...]] = (
    FAMITRACKER_FILTER,
    FileFilter(name="Bitphase project", patterns=("*.btp",)),
    PRESET_FILTER,
)

Call = Tuple[str, str, Optional[Path], Tuple[FileFilter, ...]]


class FakeBackend:
    """A backend answering with one prepared path, and the type it reports having been chosen."""

    def __init__(
        self,
        result: Optional[Path],
        reported_type: Optional[FileFilter] = None,
    ) -> None:
        self._result = result
        self._reported_type = reported_type
        self.calls: List[Call] = []

    def open_file(
        self, *, title: str, initial_directory: Optional[Path], filters: Tuple[FileFilter, ...]
    ) -> Optional[Path]:
        self.calls.append(("open", title, initial_directory, filters))
        return self._result

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]:
        self.calls.append(("save", title, initial_directory, filters))
        if self._result is None:
            return None

        return SaveDestination(path=self._result, file_type=self._reported_type)

    def select_directory(self, *, title: str, initial_directory: Optional[Path]) -> Optional[Path]:
        self.calls.append(("directory", title, initial_directory, ()))
        return self._result


class TestSaveFileDialog:
    def test_appends_missing_extension(self) -> None:
        backend = FakeBackend(Path("/home/user/song"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=(PROJECT_FILTER,))

        assert result == Path("/home/user/song.stp")
        assert backend.calls[0][3] == (PROJECT_FILTER,)

    def test_keeps_present_extension(self) -> None:
        backend = FakeBackend(Path("/home/user/song.stp"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=(PROJECT_FILTER,))

        assert result == Path("/home/user/song.stp")

    def test_cancel_returns_none(self) -> None:
        backend = FakeBackend(None)
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=(PROJECT_FILTER,))

        assert result is None

    def test_a_bare_name_takes_the_first_of_several_offered_types(self) -> None:
        backend = FakeBackend(Path("/home/user/kick"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/kick.fti")

    def test_a_typed_extension_chooses_among_several_offered_types(self) -> None:
        backend = FakeBackend(Path("/home/user/kick.json"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/kick.json")

    def test_the_reported_type_names_a_bare_name(self) -> None:
        backend = FakeBackend(Path("/home/user/kick"), reported_type=PRESET_FILTER)
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/kick.json")

    def test_a_typed_extension_stands_over_the_reported_type(self) -> None:
        """Typing an offered extension names the type, whichever one the selector stood on."""
        backend = FakeBackend(Path("/home/user/kick.fti"), reported_type=PRESET_FILTER)
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/kick.fti")

    def test_an_extension_outside_the_offered_types_takes_the_reported_one(self) -> None:
        backend = FakeBackend(Path("/home/user/kick.xm"), reported_type=PRESET_FILTER)
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/kick.xm.json")

    def test_a_dotted_name_is_saved_as_the_governing_type(self) -> None:
        """A name carrying dots of its own keeps them, so ``Kick 1.2`` saves as a file of the
        type the dialog stood on rather than one named after its trailing segment.
        """
        backend = FakeBackend(Path("/home/user/Kick 1.2"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=INSTRUMENT_FILTERS)

        assert result == Path("/home/user/Kick 1.2.fti")

    def test_one_offered_type_is_saved_as_that_type(self) -> None:
        backend = FakeBackend(Path("/home/user/Kick 1.2"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save", filters=(PROJECT_FILTER,))

        assert result == Path("/home/user/Kick 1.2.stp")

    def test_without_extension_no_filter_and_no_append(self) -> None:
        backend = FakeBackend(Path("/home/user/song"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = save_file_dialog(title="Save")

        assert result == Path("/home/user/song")
        assert backend.calls[0][3] == ()


class TestOpenFileDialog:
    def test_builds_filter_and_converts_directory(self) -> None:
        backend = FakeBackend(Path("/audio/clip.wav"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = open_file_dialog(
                title="Open",
                initial_directory="/audio",
                filters=(FileFilter.for_extensions("Audio files", [".wav", ".mp3"]),),
            )

        assert result == Path("/audio/clip.wav")
        _, _, initial_directory, filters = backend.calls[0]
        assert initial_directory == Path("/audio")
        assert filters == (FileFilter(name="Audio files", patterns=("*.wav", "*.mp3")),)


class TestSelectDirectoryDialog:
    def test_passes_through(self) -> None:
        backend = FakeBackend(Path("/audio/library"))
        with patch(f"{MODULE}.select_file_dialog_backend", return_value=backend):
            result = select_directory_dialog(title="Choose", initial_directory="/audio")

        assert result == Path("/audio/library")
        assert backend.calls[0] == ("directory", "Choose", Path("/audio"), ())
