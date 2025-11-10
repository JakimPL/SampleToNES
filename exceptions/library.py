class LibraryException(Exception):
    """Base class for exceptions raised by the library."""

    pass


class NoLibraryDataError(LibraryException):
    """Exception raised when no library data is found for the given configuration and window."""

    pass
