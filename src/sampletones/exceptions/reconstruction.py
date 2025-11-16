class ReconstructionError(Exception):
    """Base class for reconstruction errors."""

    pass


class InvalidReconstructionError(ReconstructionError):
    """Raised when an instruction is invalid or malformed."""

    pass


class IncompatibleReconstructionVersionError(ReconstructionError):
    """Raised when the reconstruction data version is incompatible."""

    def __init__(self, message: str, expected_version: str, actual_version: str) -> None:
        self.expected_version = expected_version
        self.actual_version = actual_version
        super().__init__(message)
