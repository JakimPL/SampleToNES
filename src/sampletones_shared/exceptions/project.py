from .base import SampleToNESError
from .validation import InvalidDataError, InvalidValuesError
from .version import IncompatibleVersionError


class ProjectError(SampleToNESError):
    """Base class for project errors."""


class LoadProjectError(ProjectError):
    """Exception raised when there is an error loading the project."""


class IncompatibleProjectVersionError(IncompatibleVersionError, LoadProjectError):
    """Raised when the project file format version differs from the supported version."""


class NotAValidArchiveError(LoadProjectError):
    """Raised when the project is not a valid archive file."""


class IncorrectReconstructionDataError(InvalidDataError, LoadProjectError):
    """Raised when the project contains invalid reconstruction data."""


class InvalidProjectDataValuesError(InvalidValuesError, LoadProjectError):
    """Raised when the project data are invalid."""


class MissingProjectDataFileError(LoadProjectError):
    """Raised when the project archive is missing a file."""


class UnhandledProjectError(LoadProjectError):
    """Raised when an unhandled error is encountered while loading a project."""
