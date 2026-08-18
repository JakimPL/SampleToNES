from .base import SampleToNESError


class PlayerError(SampleToNESError):
    """Base class for NES player errors."""


class SongTooLargeError(PlayerError):
    """Raised when a song's data outgrows the space the player has for it."""
