from pathlib import Path
from tkinter import Tk, filedialog
from typing import Callable, List, Optional, Tuple

from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_shared.utils.system.paths import normalize_path


class TkinterBackend:
    """
    File dialogs backed by ``tkinter.filedialog``.

    Tk renders the platform's native dialog on Windows and macOS, which makes this the
    backend there; on Linux it is the last resort when neither kdialog nor zenity is
    installed. Each call raises a transient hidden root so the dialog owns no lasting
    window.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        return _run(
            lambda: filedialog.askopenfilename(
                title=title,
                initialdir=_initial_directory(initial_directory),
                filetypes=_filetypes(file_filter),
            )
        )

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        return _run(
            lambda: filedialog.asksaveasfilename(
                title=title,
                initialdir=_initial_directory(initial_directory),
                initialfile=suggested_name or "",
                filetypes=_filetypes(file_filter),
            )
        )

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        return _run(
            lambda: filedialog.askdirectory(
                title=title,
                initialdir=_initial_directory(initial_directory),
            )
        )


def _initial_directory(initial_directory: Optional[Path]) -> Optional[str]:
    return str(initial_directory) if initial_directory is not None else None


def _filetypes(
    file_filter: Optional[FileFilter],
) -> List[Tuple[str, Tuple[str, ...]]]:
    if file_filter is None:
        return []

    return [(file_filter.label, tuple(file_filter.patterns))]


def _run(dialog: Callable[[], str]) -> Optional[Path]:
    root = Tk()
    root.withdraw()
    try:
        selection = dialog()
    finally:
        root.destroy()

    return normalize_path(selection)
