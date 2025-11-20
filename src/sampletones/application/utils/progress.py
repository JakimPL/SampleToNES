import sys

from sampletones.constants.application import SAMPLETONES_NAME
from sampletones.utils.logger import logger


class SystemProgress:
    def __init__(self) -> None:
        self.progress = None
        self.value = 0
        self.maximum = 0

    def initialize(self):
        if not sys.platform.startswith("win"):
            return

        try:
            import win32gui
            from PyTaskbar import Progress

            hwnd = win32gui.FindWindow(SAMPLETONES_NAME, None)
            if not hwnd:
                logger.warning("Could not find application window handle for progress bar")
                return

            self.progress = Progress(hwnd)
        except (ModuleNotFoundError, ImportError) as exception:
            logger.warning(f"Could not import Windows progress bar dependencies: {exception}")

    def error(self):
        if self.progress is not None:
            self.progress.set_progress_type(15)

    def start(self, maximum: int):
        self.value = 0
        self.maximum = maximum
        if self.progress is not None:
            self.progress.set_progress_type(0)
            self.progress.set_progress(0, self.maximum)

    def set(self, value: int, maximum: int):
        self.value = min(maximum, max(self.value, value))
        self.maximum = maximum
        if self.progress is not None:
            self.progress.set_progress(self.value, self.maximum)

    def clear(self):
        if self.progress is not None:
            self.progress.set_progress(0, 1)
