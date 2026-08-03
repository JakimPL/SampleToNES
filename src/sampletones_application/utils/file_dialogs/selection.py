import importlib.util
import os
import shutil
from typing import Final, Optional

from sampletones_application.utils.file_dialogs.backend import FileDialogBackend
from sampletones_application.utils.file_dialogs.kdialog import KDialogBackend
from sampletones_application.utils.file_dialogs.zenity import ZenityBackend
from sampletones_shared.exceptions import FileDialogUnavailableError
from sampletones_shared.utils.system.system import System

KDIALOG: Final[str] = "kdialog"
ZENITY: Final[str] = "zenity"
TKINTER_MODULE: Final[str] = "tkinter"
JEEPNEY_MODULE: Final[str] = "jeepney"
DESKTOP_ENVIRONMENT_VARIABLE: Final[str] = "XDG_CURRENT_DESKTOP"
KDE_DESKTOP: Final[str] = "KDE"

LINUX_REMEDY: Final[str] = "Install zenity or kdialog, or the Tk bindings for Python (Debian: python3-tk)."
REMEDY: Final[str] = "Install a Python distribution that includes Tk."


def select_file_dialog_backend() -> FileDialogBackend:
    """
    Returns the file-dialog backend that fits the running environment.

    On Linux the choice follows the desktop portal, then the desktop environment and its installed
    tools, with ``tkinter`` as the last resort; on other platforms ``tkinter`` drives the native
    dialog. Availability is probed for each candidate, so an environment lacking Tk opens dialogs
    through the desktop tools instead.

    Raises:
        FileDialogUnavailableError: If the environment provides no usable backend.
    """
    backend: Optional[FileDialogBackend]
    remedy: str
    match System.current():
        case System.LINUX:
            backend, remedy = _select_linux_backend(), LINUX_REMEDY
        case _:
            backend, remedy = _tkinter_backend(), REMEDY

    if backend is None:
        raise FileDialogUnavailableError(f"No file dialog backend is available. {remedy}")

    return backend


def _select_linux_backend() -> Optional[FileDialogBackend]:
    """
    Returns the Linux backend to open dialogs with, in order of what each dialog can express.

    The desktop portal comes first: it lists every offered file type in its selector and reports
    the one the user picked, so a caller offering several types learns which was chosen. Behind
    it stand the desktop's own command-line tools, and Tk last.
    """
    kdialog = KDialogBackend() if shutil.which(KDIALOG) is not None else None
    zenity = ZenityBackend() if shutil.which(ZENITY) is not None else None

    preferred: Optional[FileDialogBackend]
    alternative: Optional[FileDialogBackend]
    if _prefers_kde():
        preferred, alternative = kdialog, zenity
    else:
        preferred, alternative = zenity, kdialog

    return _portal_backend() or preferred or alternative or _tkinter_backend()


def _portal_backend() -> Optional[FileDialogBackend]:
    """
    Returns a portal-backed implementation once ``jeepney`` is installed and a portal answers.

    ``jeepney`` is declared for Linux alone, so its presence is probed before the portal module
    is imported, which leaves application startup on every other platform independent of it.
    """
    if importlib.util.find_spec(JEEPNEY_MODULE) is None:
        return None

    from sampletones_application.utils.file_dialogs.portal.backend import portal_backend

    return portal_backend()


def _tkinter_backend() -> Optional[FileDialogBackend]:
    """
    Returns a Tk-backed implementation once the ``tkinter`` module is importable.

    Tk ships as a separate system package on several Linux distributions, so its presence is
    probed before the backend module is imported. Keeping the import inside this function leaves
    application startup independent of Tk.
    """
    if importlib.util.find_spec(TKINTER_MODULE) is None:
        return None

    from sampletones_application.utils.file_dialogs.tkinter_backend import TkinterBackend

    return TkinterBackend()


def _prefers_kde() -> bool:
    desktop = os.environ.get(DESKTOP_ENVIRONMENT_VARIABLE, "")
    return KDE_DESKTOP in desktop.upper()
