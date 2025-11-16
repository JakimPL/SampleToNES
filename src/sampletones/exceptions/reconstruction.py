from .base import SampleToNESError
from .validation import InvalidValuesError
from .version import IncompatibleVersionError


class ReconstructionError(SampleToNESError):
    """Base class for reconstruction errors."""

    pass


class InvalidReconstructionError(ReconstructionError):
    """Raised when an instruction is invalid or malformed."""

    pass


class InvalidReconstructionValuesError(InvalidValuesError, InvalidReconstructionError):
    """Raised when reconstruction data contains invalid values."""

    pass


class IncompatibleReconstructionVersionError(IncompatibleVersionError, ReconstructionError):
    """Raised when the reconstruction data version is incompatible."""

    pass
