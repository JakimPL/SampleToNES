from pathlib import Path
from tkinter import Tk, filedialog
from typing import Callable, List, Optional, Tuple

from sampletones_application.utils.file_dialogs.destination import (
    SaveDestination,
    untyped_destination,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_shared.utils.system.paths import normalize_path


class TkinterBackend:
    """
    File dialogs backed by ``tkinter.filedialog``.

    Tk renders the platform's native dialog on Windows and macOS, which makes this the
    backend there; on Linux it is the last resort when neither kdialog nor zenity is
    installed. Every offered type reaches the dialog's type selector as its own entry.
    Each call raises a transient hidden root so the dialog owns no lasting window.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        return self._run(
            lambda: filedialog.askopenfilename(
                title=title,
                initialdir=self._initial_directory(initial_directory),
                filetypes=self._filetypes(filters),
            )
        )

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]:
        return untyped_destination(
            self._run(
                lambda: filedialog.asksaveasfilename(
                    title=title,
                    initialdir=self._initial_directory(initial_directory),
                    initialfile=suggested_name or "",
                    filetypes=self._filetypes(filters),
                )
            )
        )

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        return self._run(
            lambda: filedialog.askdirectory(
                title=title,
                initialdir=self._initial_directory(initial_directory),
            )
        )

    @staticmethod
    def _initial_directory(initial_directory: Optional[Path]) -> Optional[str]:
        return str(initial_directory) if initial_directory is not None else None

    @staticmethod
    def _filetypes(
        filters: Tuple[FileFilter, ...],
    ) -> List[Tuple[str, Tuple[str, ...]]]:
        return [(file_filter.label, file_filter.patterns) for file_filter in filters]

    @staticmethod
    def _run(dialog: Callable[[], str]) -> Optional[Path]:
        root = Tk()
        root.withdraw()
        try:
            selection = dialog()
        finally:
            root.destroy()

        return normalize_path(selection)
