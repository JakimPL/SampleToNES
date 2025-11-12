class BaseWindowError(Exception):
    """Base exception for window-related errors."""

    pass


class WindowNotAvailableError(BaseWindowError):
    """Exception raised when the application window is not available."""

    pass
