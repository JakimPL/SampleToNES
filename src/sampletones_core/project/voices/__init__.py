from .creation import new_instrument
from .envelopes import InstrumentEnvelopes
from .instrument import Instrument
from .note_off import NoteOff
from .note_on import NoteOn
from .record import SampleRecord, VoiceRecord
from .sample import Sample
from .voice import VoiceUnion, samples, voice_channels, voice_reference

__all__ = [
    "Instrument",
    "InstrumentEnvelopes",
    "NoteOff",
    "NoteOn",
    "Sample",
    "SampleRecord",
    "VoiceRecord",
    "VoiceUnion",
    "new_instrument",
    "samples",
    "voice_channels",
    "voice_reference",
]
