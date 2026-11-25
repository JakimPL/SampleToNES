from collections import Counter
from typing import Dict, Final, FrozenSet, Mapping, NamedTuple, Optional, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import TONE_CHANNELS, ChannelName, GeneratorClassName, ordered_channels
from sampletones_core.generators import (
    PulseGenerator,
    TonalGeneratorUnion,
    TriangleGenerator,
    get_generators_by_channels,
)
from sampletones_core.instructions import TonalInstruction

from .frames import Frame
from .intervals import semitones_between

UNBENT: Final[int] = 0
TONAL_CHANNELS: Final[Tuple[ChannelName, ...]] = tuple(ordered_channels(TONE_CHANNELS))
INVERTED_DUTY_CYCLES: Final[Dict[int, int]] = {3: 1}


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
    naming the same pitch. It is read unbent, at the pitch the frame names, so a bend leaves the note it
    bends. Both pulses are one kind, so a frame holds a note once however many pulses sound it.
    Semitones are counted on the library's tuning, from its A4.
    """

    def __init__(self, config: Config) -> None:
        self._generators: Dict[ChannelName, TonalGeneratorUnion] = {}
        for channel, generator in get_generators_by_channels(config, list(TONAL_CHANNELS)).items():
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
        return round(semitones_between(frequency, self._a4_frequency) + self._a4_pitch)


def pitch_counts(notes: FrozenSet[Note]) -> Counter[int]:
    """How many of a frame's notes sound each semitone, whichever channel kind sounds each.

    A semitone two channel kinds sound together counts twice, so two frames hold equal counts where
    each note of one pairs with a note of the other at its pitch, one to one.
    """
    return Counter(note.semitone for note in notes)


def timbre_of(duty_cycle: int) -> int:
    """The timbre a pulse's duty cycle sounds: 75% is the 25% wave inverted, which the ear hears as the same."""
    return INVERTED_DUTY_CYCLES.get(duty_cycle, duty_cycle)
