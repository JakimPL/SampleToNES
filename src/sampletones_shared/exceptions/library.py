from .base import SampleToNESError
from .validation import InvalidValuesError
from .version import IncompatibleVersionError


class LibraryError(SampleToNESError):
    """Base class for exceptions raised by the library."""


class NoLibraryDataError(LibraryError):
    """Exception raised when no library data is found for the given configuration and window."""


class LoadLibraryError(LibraryError):
    """Exception raised when there is an error loading the library."""


class InvalidLibraryDataError(LoadLibraryError):
    """Exception raised when the library data is invalid or corrupted."""


class InstructionTypeMismatchError(InvalidLibraryDataError):
    """Raised when the instruction type does not match the expected class."""


class InvalidLibraryDataValuesError(InvalidValuesError, InvalidLibraryDataError):
    """Raised when library data contains invalid values."""


class IncompatibleLibraryDataVersionError(IncompatibleVersionError, LoadLibraryError):
    """Raised when the library data version is incompatible."""


class LibraryDisplayError(LibraryError):
    """Exception raised when there is an error loading library data."""
