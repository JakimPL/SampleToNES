import os
import subprocess
from pathlib import Path
from typing import List, Optional

from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_shared.utils.system.paths import normalize_path


class ZenityBackend:
    """
    File dialogs backed by GNOME's ``zenity`` (GTK).

    The named filter appears in the file-type selector. ``zenity`` lists the filter
    but leaves the selector on its "(None)" entry, since its command line offers no
    way to pre-select a filter; the extension is still guaranteed by the API layer.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        command = ["zenity", "--file-selection", "--title", title]
        command += _filename_arguments(initial_directory, None)
        command += _filter_arguments(file_filter)
        return _run(command)

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]:
        command = ["zenity", "--file-selection", "--save", "--confirm-overwrite", "--title", title]
        command += _filename_arguments(initial_directory, suggested_name)
        command += _filter_arguments(file_filter)
        return _run(command)

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        command = ["zenity", "--file-selection", "--directory", "--title", title]
        command += _filename_arguments(initial_directory, None)
        return _run(command)


def _filename_arguments(initial_directory: Optional[Path], suggested_name: Optional[str]) -> List[str]:
    if initial_directory is None and not suggested_name:
        return []

    base = initial_directory if initial_directory is not None else Path.home()
    if suggested_name:
        return ["--filename", str(base / suggested_name)]

    return ["--filename", f"{base}{os.sep}"]


def _filter_arguments(file_filter: Optional[FileFilter]) -> List[str]:
    if file_filter is None:
        return []

    patterns = " ".join(file_filter.patterns)
    return ["--file-filter", f"{file_filter.label} | {patterns}"]


def _run(command: List[str]) -> Optional[Path]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return normalize_path(result.stdout.strip())
