import math
from typing import Dict, Final, FrozenSet, Mapping, NamedTuple, Optional

from sampletones_core.configs import Config
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, GeneratorClassName
from sampletones_core.generators import (
    PulseGenerator,
    TonalGeneratorUnion,
    TriangleGenerator,
    get_generators_by_channels,
)
from sampletones_core.instructions import TonalInstruction
from sampletones_shared.constants.music import OCTAVE_SEMITONES

from .frames import Frame

UNBENT: Final[int] = 0


class Note(NamedTuple):
    """A note a tonal channel kind sounds in one frame.

    Attributes:
        kind: The kind of channel sounding it; both pulses are one kind.
        semitone: The equal-tempered semitone it sounds at, the octave the channel puts it in included.
    """

    kind: GeneratorClassName
    semitone: int


class NoteReader:
    """Reads the notes a frame's tonal channels sound, so frames are compared by what is heard.

    A note is read at the semitone its channel sounds, which puts a triangle an octave under a pulse
    naming the same pitch, and a bend leaves the note it bends. Both pulses are one kind, so a frame
    holds a note once however many pulses sound it.
    """

    def __init__(self, config: Config) -> None:
        tonal = [channel for channel in ChannelName.items() if channel in TONE_CHANNELS]
        self._generators: Dict[ChannelName, TonalGeneratorUnion] = {}
        for channel, generator in get_generators_by_channels(config, tonal).items():
            match generator:
                case PulseGenerator() | TriangleGenerator():
                    self._generators[channel] = generator

        self._a4_frequency = config.library.a4_frequency
        self._a4_pitch = config.library.a4_pitch

    def note(self, channel: ChannelName, frame: Frame) -> Optional[Note]:
        """The note ``frame`` sounds on ``channel``, or ``None`` where it sounds none."""
        generator = self._generators.get(channel)
        match frame:
            case TonalInstruction(on=True) if generator is not None:
                frequency = generator.sounds_at(frame.pitch, UNBENT)
                return Note(kind=generator.class_name(), semitone=self._semitone(frequency))
            case _:
                return None

    def notes(self, frames: Mapping[ChannelName, Frame]) -> FrozenSet[Note]:
        """The notes one frame of every channel sounds together."""
        sounded = (self.note(channel, frame) for channel, frame in frames.items())
        return frozenset(note for note in sounded if note is not None)

    def _semitone(self, frequency: float) -> int:
        return round(OCTAVE_SEMITONES * math.log2(frequency / self._a4_frequency) + self._a4_pitch)


def pitches_of(notes: FrozenSet[Note]) -> FrozenSet[int]:
    """The semitones a frame's notes sound, whichever channel kind sounds each."""
    return frozenset(note.semitone for note in notes)
