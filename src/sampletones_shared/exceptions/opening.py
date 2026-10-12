from .base import SampleToNESError


class FileNotOpenedError(SampleToNESError, OSError):
    """Raised when no program on the system takes a file to show."""
