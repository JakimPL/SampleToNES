import sys

from sampletones.constants.application import SAMPLETONES_NAME


class SystemProgress:
    def __init__(self) -> None:
        self.progress = None
        self.value = 0
        self.maximum = 0

    def _win_start(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.set_progress_type(0)
        self.progress.set_progress(0, self.maximum)

    def _win_set(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.set_progress(self.value, self.maximum)

    def _win_error(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.set_progress_type(15)

    def _win_clear(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.set_progress(0, 100)

    def _mac_start(self):
        pass  # Not implemented

    def _mac_set(self):
        pass  # Not implemented

    def _mac_error(self):
        pass  # Not implemented

    def _mac_clear(self):
        pass  # Not implemented

    def _linux_start(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.showProgress(SAMPLETONES_NAME, 0.0)

    def _linux_set(self):
        assert self.progress is not None, "Progress bar not initialized"
        progress = self.value / self.maximum if self.maximum > 0 else 1.0
        self.progress.showProgress(SAMPLETONES_NAME, progress)

    def _linux_error(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.showProgress(SAMPLETONES_NAME, -1.0)

    def _linux_clear(self):
        assert self.progress is not None, "Progress bar not initialized"
        self.progress.hideProgress(SAMPLETONES_NAME)

    def initialize(self):
        if sys.platform.startswith("win"):
            import win32gui
            from PyTaskbar import Progress

            hwnd = win32gui.FindWindow(SAMPLETONES_NAME, None)
            if not hwnd:
                raise RuntimeError("Could not find application window handle for progress bar")

            self.progress = Progress(hwnd)

        if sys.platform == "darwin":
            pass  # Not implemented

        if sys.platform.startswith("linux"):
            try:
                from pydbus import SessionBus

                bus = SessionBus()
                self.progress = bus.get("org.kde.plasmashell")
            except (ModuleNotFoundError, ImportError):
                self.progress = None

    def error(self):
        if sys.platform.startswith("win"):
            return self._win_error()

        if sys.platform == "darwin":
            return self._mac_error()

        if sys.platform.startswith("linux"):
            return self._linux_error()

        return None

    def start(self, maximum: int):
        self.value = 0
        self.maximum = maximum

        if sys.platform.startswith("win"):
            return self._win_start()

        if sys.platform == "darwin":
            return self._mac_start()

        if sys.platform.startswith("linux"):
            return self._linux_start()

        return None

    def set(self, value: int, maximum: int):
        self.value = min(maximum, max(self.value, value))
        self.maximum = maximum

        if sys.platform.startswith("win"):
            return self._win_set()

        if sys.platform == "darwin":
            return self._mac_set()

        if sys.platform.startswith("linux"):
            return self._linux_set()

        return None

    def clear(self):
        if sys.platform.startswith("win"):
            return self._win_clear()

        if sys.platform == "darwin":
            return self._mac_clear()

        if sys.platform.startswith("linux"):
            return self._linux_clear()

        return None
