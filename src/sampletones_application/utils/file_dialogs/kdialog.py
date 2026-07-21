import subprocess
from pathlib import Path
from typing import List, Optional

from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_shared.utils.system.paths import normalize_path


class KDialogBackend:
    """
    File dialogs backed by KDE's ``kdialog`` (Qt).

    ``kdialog`` activates the supplied filter, so the file-type selector opens on the
    chosen type rather than an unfiltered default.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        command = ["kdialog", "--getopenfilename", _start_location(initial_directory)]
        command += _filter_arguments(file_filter)
        command += ["--title", title]
        return _run(command)

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        command = ["kdialog", "--getsavefilename", _start_location(initial_directory, suggested_name)]
        command += _filter_arguments(file_filter)
        command += ["--title", title]
        return _run(command)

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        command = ["kdialog", "--getexistingdirectory", _start_location(initial_directory), "--title", title]
        return _run(command)


def _start_location(initial_directory: Optional[Path], suggested_name: Optional[str] = None) -> str:
    base = initial_directory if initial_directory is not None else Path.home()
    if suggested_name:
        return str(base / suggested_name)

    return str(base)


def _filter_arguments(file_filter: Optional[FileFilter]) -> List[str]:
    if file_filter is None:
        return []

    patterns = " ".join(file_filter.patterns)
    return [f"{patterns}|{file_filter.label}"]


def _run(command: List[str]) -> Optional[Path]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return normalize_path(result.stdout.strip())
