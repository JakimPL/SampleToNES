from .base import SampleToNESError
from .validation import InvalidValuesError
from .version import IncompatibleVersionError


class InstrumentError(SampleToNESError):
    """Base class for instrument file errors."""


class LoadInstrumentError(InstrumentError):
    """Exception raised when there is an error loading an instrument file."""


class NotAnInstrumentFileError(LoadInstrumentError):
    """Raised when the data opens with something other than the instrument file signature."""


class IncompatibleInstrumentVersionError(IncompatibleVersionError, LoadInstrumentError):
    """Raised when the instrument file states a layout version other than the supported one."""


class UnsupportedInstrumentTypeError(LoadInstrumentError):
    """Raised when the instrument file states a chip other than the one read here."""


class MalformedInstrumentError(LoadInstrumentError):
    """Raised when an instrument file departs from the layout its own fields describe."""


class InvalidInstrumentValuesError(InvalidValuesError, LoadInstrumentError):
    """Raised when instrument data contains invalid values."""
