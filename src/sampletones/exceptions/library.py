class LibraryError(Exception):
    """Base class for exceptions raised by the library."""

    pass


class NoLibraryDataError(LibraryError):
    """Exception raised when no library data is found for the given configuration and window."""

    pass


class LoadLibraryError(LibraryError):
    """Exception raised when there is an error loading the library."""

    pass


class LibraryDisplayError(LibraryError):
    """Exception raised when there is an error loading library data."""

    pass
