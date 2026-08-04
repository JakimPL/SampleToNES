import os
from pathlib import Path
from typing import List, Optional, Tuple

from sampletones_application.utils.file_dialogs.backends.command import run_dialog_command
from sampletones_application.utils.file_dialogs.destination import (
    SaveDestination,
    untyped_destination,
)
from sampletones_application.utils.file_dialogs.filter import FileFilter


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
        command += self._filename_arguments(initial_directory, None)
        command += self._filter_arguments(filters)
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
            "zenity",
            "--file-selection",
            "--save",
            "--confirm-overwrite",
            "--title",
            title,
        ]
        command += self._filename_arguments(initial_directory, suggested_name)
        command += self._filter_arguments(filters)
        return untyped_destination(run_dialog_command(command))

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
        command += self._filename_arguments(initial_directory, None)
        return run_dialog_command(command)

    @staticmethod
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

    @staticmethod
    def _filter_arguments(filters: Tuple[FileFilter, ...]) -> List[str]:
        arguments: List[str] = []
        for file_filter in filters:
            patterns = " ".join(file_filter.patterns)
            arguments += ["--file-filter", f"{file_filter.label} | {patterns}"]

        return arguments
