from sampletones_shared.exceptions import SampleToNESError
from sampletones_shared.exceptions.validation import InvalidDataError


class ConsoleError(SampleToNESError):
    """The console could not run a file to the end of a routine."""


class NotAnNSFError(InvalidDataError):
    """The data a console was handed is no NSF file: its header lacks the NSF signature."""


class RoutineOverrunError(ConsoleError):
    """A routine ran for its whole step budget without returning to the caller."""
