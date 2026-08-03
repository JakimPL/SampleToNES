from pathlib import Path
from unittest.mock import patch

from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_application.utils.file_dialogs.tkinter_backend import TkinterBackend

MODULE = "sampletones_application.utils.file_dialogs.tkinter_backend"


class TestTkinterBackend:
    def test_save_passes_filetypes_and_disposes_root(self) -> None:
        backend = TkinterBackend()
        file_filter = FileFilter(name="Project files", patterns=("*.stp",))
        with patch(f"{MODULE}.Tk") as tk, patch(f"{MODULE}.filedialog") as filedialog:
            filedialog.asksaveasfilename.return_value = "/home/user/song.stp"
            result = backend.save_file(
                title="Save",
                initial_directory=Path("/home/user"),
                suggested_name="song",
                filters=(file_filter,),
            )

        kwargs = filedialog.asksaveasfilename.call_args.kwargs
        assert result == SaveDestination(path=Path("/home/user/song.stp"), file_type=None)
        assert kwargs["filetypes"] == [("Project files (*.stp)", ("*.stp",))]
        assert kwargs["initialfile"] == "song"
        assert kwargs["initialdir"] == str(Path("/home/user"))
        tk.return_value.withdraw.assert_called_once()
        tk.return_value.destroy.assert_called_once()

    def test_each_offered_type_becomes_its_own_filetype(self) -> None:
        backend = TkinterBackend()
        filters = (
            FileFilter(name="FamiTracker instrument", patterns=("*.fti",)),
            FileFilter(name="Bitphase preset", patterns=("*.json",)),
        )
        with patch(f"{MODULE}.Tk"), patch(f"{MODULE}.filedialog") as filedialog:
            filedialog.asksaveasfilename.return_value = "/home/user/kick.json"
            backend.save_file(
                title="Export instrument",
                initial_directory=None,
                suggested_name="kick",
                filters=filters,
            )

        kwargs = filedialog.asksaveasfilename.call_args.kwargs
        assert kwargs["filetypes"] == [
            ("FamiTracker instrument (*.fti)", ("*.fti",)),
            ("Bitphase preset (*.json)", ("*.json",)),
        ]

    def test_open_without_filter_uses_empty_filetypes(self) -> None:
        backend = TkinterBackend()
        with patch(f"{MODULE}.Tk"), patch(f"{MODULE}.filedialog") as filedialog:
            filedialog.askopenfilename.return_value = ""
            result = backend.open_file(title="Open", initial_directory=None, filters=())

        kwargs = filedialog.askopenfilename.call_args.kwargs
        assert result is None
        assert kwargs["filetypes"] == []
        assert kwargs["initialdir"] is None

    def test_directory_returns_path(self) -> None:
        backend = TkinterBackend()
        with patch(f"{MODULE}.Tk"), patch(f"{MODULE}.filedialog") as filedialog:
            filedialog.askdirectory.return_value = "/audio/library"
            result = backend.select_directory(title="Choose", initial_directory=Path("/audio"))

        assert result == Path("/audio/library")
