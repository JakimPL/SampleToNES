from pathlib import Path
from unittest.mock import patch

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
                file_filter=file_filter,
            )

        kwargs = filedialog.asksaveasfilename.call_args.kwargs
        assert result == Path("/home/user/song.stp")
        assert kwargs["filetypes"] == [("Project files (*.stp)", ("*.stp",))]
        assert kwargs["initialfile"] == "song"
        assert kwargs["initialdir"] == "/home/user"
        tk.return_value.withdraw.assert_called_once()
        tk.return_value.destroy.assert_called_once()

    def test_open_without_filter_uses_empty_filetypes(self) -> None:
        backend = TkinterBackend()
        with patch(f"{MODULE}.Tk"), patch(f"{MODULE}.filedialog") as filedialog:
            filedialog.askopenfilename.return_value = ""
            result = backend.open_file(title="Open", initial_directory=None, file_filter=None)

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
