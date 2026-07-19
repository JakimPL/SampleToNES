from pathlib import Path
from typing import Optional, Protocol

from sampletones_application.utils.file_dialogs.filter import FileFilter


class FileDialogBackend(Protocol):
    """
    A native file-dialog implementation for one platform or desktop tool.

    An implementation drives a system dialog (kdialog, zenity) or ``tkinter`` and
    returns the chosen path, yielding ``None`` when the user cancels. The selector in
    ``selection`` picks the implementation that fits the running environment.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]: ...

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        file_filter: Optional[FileFilter],
    ) -> Optional[Path]: ...

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]: ...
