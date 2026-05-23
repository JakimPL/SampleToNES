from .base import SampleToNESError
from .validation import InvalidValuesError
from .version import IncompatibleVersionError


class ReconstructionError(SampleToNESError):
    """Base class for reconstruction errors."""


class LoadReconstructionError(ReconstructionError):
    """Exception raised when there is an error loading the reconstruction."""


class InvalidReconstructionError(LoadReconstructionError):
    """Raised when an instruction is invalid or malformed."""


class InvalidReconstructionValuesError(InvalidValuesError, InvalidReconstructionError):
    """Raised when reconstruction data contains invalid values."""


class IncompatibleReconstructionVersionError(IncompatibleVersionError, LoadReconstructionError):
    """Raised when the reconstruction data version is incompatible."""


class NoFilesToProcessError(ReconstructionError):
    """Raised when there are no files to process during reconstruction."""
