class ReconstructionError(Exception):
    """Base class for reconstruction errors."""

    pass


class InvalidReconstructionError(ReconstructionError):
    """Raised when an instruction is invalid or malformed."""

    pass


class IncompatibleReconstructionVersionError(ReconstructionError):
    """Raised when the reconstruction data version is incompatible."""

    pass
