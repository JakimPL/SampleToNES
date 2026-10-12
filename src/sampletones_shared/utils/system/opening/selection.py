import os
import shutil
import sys

from sampletones_shared.utils.system.system import System

from .browser import BrowserFileOpener
from .protocol import FileOpener
from .xdg_open import XDG_OPEN, XdgOpenFileOpener


def select_file_opener() -> FileOpener:
    """The file opener that fits the running system.

    A Linux desktop with ``xdg-open`` opens a file through it, the one way a bundle hands the
    program the reader's own library path; every other system opens it through the standard
    library's browser support.
    """
    if System.current() == System.LINUX and shutil.which(XDG_OPEN) is not None:
        return XdgOpenFileOpener(os.environ, frozen=running_frozen())

    return BrowserFileOpener()


def running_frozen() -> bool:
    """Whether the application runs from a PyInstaller bundle, which marks ``sys`` as frozen."""
    return bool(getattr(sys, "frozen", False))
