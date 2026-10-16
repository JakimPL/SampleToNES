from .base import SampleToNESError


class MidiPortError(SampleToNESError):
    """Raised when a MIDI library fails to list, open or read an input port, in the library's own words."""
