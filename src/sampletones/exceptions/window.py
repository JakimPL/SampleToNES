from .base import SampleToNESError


class WindowError(SampleToNESError):
    """Base exception for window-related errors."""

    pass


class WindowNotAvailableError(WindowError):
    """Exception raised when the application window is not available."""

    pass
