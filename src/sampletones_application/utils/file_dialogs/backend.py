from pathlib import Path
from typing import Optional, Protocol, Tuple

from sampletones_application.utils.file_dialogs.destination import SaveDestination
from sampletones_application.utils.file_dialogs.filter import FileFilter


class FileDialogBackend(Protocol):
    """
    A native file-dialog implementation for one platform or desktop tool.

    An implementation drives a system dialog (the desktop portal, kdialog, zenity) or
    ``tkinter`` and returns the chosen path, yielding ``None`` when the user cancels. The
    selector in ``selection`` picks the implementation that fits the running environment.

    ``filters`` carries the types the dialog offers, in the order they are shown. Each
    implementation renders as many of them as its dialog accepts, so a caller states the
    types it writes once and every backend shows what it can. A save answers with a
    ``SaveDestination``, which carries the type the user selected for implementations whose
    dialog reports it.
    """

    def open_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[Path]: ...

    def save_file(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
        suggested_name: Optional[str],
        filters: Tuple[FileFilter, ...],
    ) -> Optional[SaveDestination]: ...

    def select_directory(
        self,
        *,
        title: str,
        initial_directory: Optional[Path],
    ) -> Optional[Path]: ...
