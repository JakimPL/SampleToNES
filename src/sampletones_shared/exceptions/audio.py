from .base import SampleToNESError


class AudioError(SampleToNESError):
    """Base class for audio-related exceptions."""


class UnsupportedAudioFormatError(AudioError):
    """Exception raised for unsupported audio formats."""


class PlaybackError(AudioError):
    """Base class for exceptions raised during playback."""


class AudioWriteError(AudioError):
    """Exception raised when audio cannot be written to a file."""
