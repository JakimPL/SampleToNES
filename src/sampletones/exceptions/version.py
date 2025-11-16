from .base import SampleToNESError


class IncompatibleVersionError(SampleToNESError):
    """Raised when the data version is incompatible."""

    def __init__(self, message: str, expected_version: str, actual_version: str) -> None:
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(message)
