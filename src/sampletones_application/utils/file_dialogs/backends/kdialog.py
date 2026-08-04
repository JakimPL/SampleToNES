from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.utils.file_dialogs.backends.command import run_dialog_command
from sampletones_application.utils.file_dialogs.destination import (
    SaveDestination,
    untyped_destination,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter, merge_filters


class KDialogBackend:
    """
    File dialogs backed by KDE's ``kdialog`` (Qt).

    ``kdialog`` activates the supplied filter, so the file-type selector opens on the
    chosen type. Its command line carries one filter, so offering a single type hands KDE
    a lone pattern and its own extension checkbox fills that extension in; several types
    gather into one filter whose label names each of them.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        command = [
            "kdialog",
            "--getopenfilename",
            self._start_location(initial_directory),
        ]
        command += self._filter_arguments(filters)
        command += ["--title", title]
        return run_dialog_command(command)

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]:
        command = [
            "kdialog",
            "--getsavefilename",
            self._start_location(
                initial_directory,
                suggested_name,
            ),
        ]
        command += self._filter_arguments(filters)
        command += ["--title", title]
        return untyped_destination(run_dialog_command(command))

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        command = [
            "kdialog",
            "--getexistingdirectory",
            self._start_location(initial_directory),
            "--title",
            title,
        ]
        return run_dialog_command(command)

    @staticmethod
    def _start_location(
        initial_directory: Optional[Path],
        suggested_name: Optional[str] = None,
    ) -> str:
        base = initial_directory if initial_directory is not None else Path.home()
        if suggested_name:
            return str(base / suggested_name)

        return str(base)

    @staticmethod
    def _filter_arguments(filters: Tuple[FileFilter, ...]) -> List[str]:
        merged = merge_filters(filters)
        if merged is None:
            return []

        patterns = " ".join(merged.patterns)
        return [f"{patterns}|{merged.label}"]
