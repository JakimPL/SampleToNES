class BaseReconstructionError(Exception):
    """Base class for reconstruction errors."""

    pass


class InvalidReconstructionError(BaseReconstructionError):
    """Raised when an instruction is invalid or malformed."""

    pass
