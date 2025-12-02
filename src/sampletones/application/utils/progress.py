import sys

from sampletones.constants.application import SAMPLETONES_NAME
from sampletones.utils.logger import logger


class SystemProgress:
    def __init__(self) -> None:
        self.progress = None
        self.value = 0
        self.maximum = 0

    def initialize(self) -> None:
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
        except Exception as exception:  # pylint: disable=broad-except
            self._fallback(exception)

    def error(self) -> None:
        if self.progress is not None:
            try:
                self.progress.set_progress_type(15)
            except Exception as exception:  # pylint: disable=broad-except
                self._fallback(exception)

    def start(self, maximum: int) -> None:
        if self.progress is not None:
            self.value = 0
            self.maximum = maximum
            try:
                self.progress.set_progress_type(0)
                self.progress.set_progress(0, self.maximum)
            except Exception as exception:  # pylint: disable=broad-except
                self._fallback(exception)

    def set(self, value: int, maximum: int) -> None:
        if self.progress is not None:
            self.value = min(maximum, max(self.value, value))
            self.maximum = maximum
            try:
                self.progress.set_progress(self.value, self.maximum)
            except Exception as exception:  # pylint: disable=broad-except
                self._fallback(exception)

    def clear(self) -> None:
        if self.progress is not None:
            try:
                self.progress.set_progress(0, 1)
            except Exception as exception:  # pylint: disable=broad-except
                self._fallback(exception)

    def _fallback(self, exception: Exception) -> None:
        logger.warning(f"Could not set Windows progress bar: {exception}")
        self.progress = None
