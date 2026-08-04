import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.utils.file_dialogs.destination import (
    SaveDestination,
    untyped_destination,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter, merge_filters
from sampletones_shared.utils.system.paths import normalize_path


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
            _start_location(initial_directory),
        ]
        command += _filter_arguments(filters)
        command += ["--title", title]
        return _run(command)

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
            _start_location(
                initial_directory,
                suggested_name,
            ),
        ]
        command += _filter_arguments(filters)
        command += ["--title", title]
        return untyped_destination(_run(command))

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        command = [
            "kdialog",
            "--getexistingdirectory",
            _start_location(initial_directory),
            "--title",
            title,
        ]
        return _run(command)


def _start_location(
    initial_directory: Optional[Path],
    suggested_name: Optional[str] = None,
) -> str:
    base = initial_directory if initial_directory is not None else Path.home()
    if suggested_name:
        return str(base / suggested_name)

    return str(base)


def _filter_arguments(filters: Tuple[FileFilter, ...]) -> List[str]:
    merged = merge_filters(filters)
    if merged is None:
        return []

    patterns = " ".join(merged.patterns)
    return [f"{patterns}|{merged.label}"]


def _run(command: List[str]) -> Optional[Path]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return normalize_path(result.stdout.strip())
