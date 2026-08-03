import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.utils.file_dialogs.destination import (
    SaveDestination,
    untyped_destination,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter
from sampletones_shared.utils.system.paths import normalize_path


class ZenityBackend:
    """
    File dialogs backed by GNOME's ``zenity`` (GTK).

    Every offered type reaches the file-type selector as its own entry, so each accepted
    extension is named on screen. GTK selects among them to narrow what the browser lists,
    and reports the name that was typed; the extension is guaranteed by the API layer.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]:
        command = ["zenity", "--file-selection", "--title", title]
        command += _filename_arguments(initial_directory, None)
        command += _filter_arguments(filters)
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
            "zenity",
            "--file-selection",
            "--save",
            "--confirm-overwrite",
            "--title",
            title,
        ]
        command += _filename_arguments(initial_directory, suggested_name)
        command += _filter_arguments(filters)
        return untyped_destination(_run(command))

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]:
        command = [
            "zenity",
            "--file-selection",
            "--directory",
            "--title",
            title,
        ]
        command += _filename_arguments(initial_directory, None)
        return _run(command)


def _filename_arguments(
    initial_directory: Optional[Path],
    suggested_name: Optional[str],
) -> List[str]:
    if initial_directory is None and not suggested_name:
        return []

    base = initial_directory if initial_directory is not None else Path.home()
    if suggested_name:
        return ["--filename", str(base / suggested_name)]

    return ["--filename", f"{base}{os.sep}"]


def _filter_arguments(filters: Tuple[FileFilter, ...]) -> List[str]:
    arguments: List[str] = []
    for file_filter in filters:
        patterns = " ".join(file_filter.patterns)
        arguments += ["--file-filter", f"{file_filter.label} | {patterns}"]

    return arguments


def _run(command: List[str]) -> Optional[Path]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    return normalize_path(result.stdout.strip())
