from .base import SampleToNESError
from .validation import InvalidValuesError
from .version import IncompatibleVersionError


class LibraryError(SampleToNESError):
    """Base class for exceptions raised by the library."""

    pass


class NoLibraryDataError(LibraryError):
    """Exception raised when no library data is found for the given configuration and window."""

    pass


class LoadLibraryError(LibraryError):
    """Exception raised when there is an error loading the library."""

    pass


class InvalidLibraryDataError(LoadLibraryError):
    """Exception raised when the library data is invalid or corrupted."""

    pass


class InvalidLibraryDataValuesError(InvalidValuesError, InvalidLibraryDataError):
    """Raised when library data contains invalid values."""

    pass


class IncompatibleLibraryDataVersionError(IncompatibleVersionError, LoadLibraryError):
    """Raised when the library data version is incompatible."""

    pass


class LibraryDisplayError(LibraryError):
    """Exception raised when there is an error loading library data."""

    pass
