import shutil

from sampletones_shared.utils.system.system import System

from .browser import BrowserFileOpener
from .protocol import FileOpener
from .xdg_open import XDG_OPEN, XdgOpenFileOpener


def select_file_opener() -> FileOpener:
    """The file opener that fits the running system.

    A Linux desktop with ``xdg-open`` opens a file through it, which hands the file to the
    desktop's own program for its kind; every other system opens it through the standard library's
    browser support.
    """
    if System.current() == System.LINUX and shutil.which(XDG_OPEN) is not None:
        return XdgOpenFileOpener()

    return BrowserFileOpener()
