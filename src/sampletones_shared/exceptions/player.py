from .base import SampleToNESError


class PlayerError(SampleToNESError):
    """Base class for NES player errors."""


class SongTooLargeError(PlayerError):
    """Raised when a song's data outgrows the space the player has for it."""


class DriverBuildError(PlayerError):
    """Raised when a driver build produces something other than the image the exporter reads."""


class ToolchainMissingError(DriverBuildError):
    """Raised when the programs a driver build runs are absent from the system."""
