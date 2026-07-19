import os
import shutil
from typing import Final, Optional

from sampletones_application.utils.file_dialogs.backend import FileDialogBackend
from sampletones_application.utils.file_dialogs.kdialog import KDialogBackend
from sampletones_application.utils.file_dialogs.tkinter_backend import TkinterBackend
from sampletones_application.utils.file_dialogs.zenity import ZenityBackend
from sampletones_shared.utils.system.system import System

KDIALOG: Final[str] = "kdialog"
ZENITY: Final[str] = "zenity"
DESKTOP_ENVIRONMENT_VARIABLE: Final[str] = "XDG_CURRENT_DESKTOP"
KDE_DESKTOP: Final[str] = "KDE"


def select_file_dialog_backend() -> FileDialogBackend:
    """
    Returns the file-dialog backend that fits the running environment.

    On Linux the choice follows the desktop environment and installed tools; on other
    platforms ``tkinter`` drives the native dialog.
    """
    match System.current():
        case System.LINUX:
            return _select_linux_backend()
        case _:
            return TkinterBackend()


def _select_linux_backend() -> FileDialogBackend:
    kdialog = KDialogBackend() if shutil.which(KDIALOG) is not None else None
    zenity = ZenityBackend() if shutil.which(ZENITY) is not None else None

    preferred: Optional[FileDialogBackend]
    alternative: Optional[FileDialogBackend]
    if _prefers_kde():
        preferred, alternative = kdialog, zenity
    else:
        preferred, alternative = zenity, kdialog

    return preferred or alternative or TkinterBackend()


def _prefers_kde() -> bool:
    desktop = os.environ.get(DESKTOP_ENVIRONMENT_VARIABLE, "")
    return KDE_DESKTOP in desktop.upper()
