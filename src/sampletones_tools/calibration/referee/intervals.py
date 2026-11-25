import math
from typing import Final, List, Optional

from sampletones_shared.constants.music import A4_FREQUENCY, OCTAVE_SEMITONES
from sampletones_tools.calibration.corpus.truth import PitchLine

CENTS_PER_SEMITONE: Final[float] = 100.0
CENTS_PER_OCTAVE: Final[float] = CENTS_PER_SEMITONE * OCTAVE_SEMITONES


def octaves_between(frequency: float, reference: float) -> float:
    """How many octaves ``frequency`` stands above ``reference``, below zero where it stands under it.

    Hearing spaces pitch by frequency ratio, so every interval the referees read is this logarithm of
    the ratio, counted in the steps each reading needs.
    """
    return math.log2(frequency / reference)


def semitones_between(frequency: float, reference: float) -> float:
    """How many equal-tempered semitones ``frequency`` stands above ``reference``."""
    return OCTAVE_SEMITONES * octaves_between(frequency, reference)


def cents_between(frequency: float, reference: float) -> float:
    """How many cents ``frequency`` stands above ``reference``, a hundred to the semitone."""
    return CENTS_PER_OCTAVE * octaves_between(frequency, reference)


def same_pitch_class(frequency: float, target: float) -> bool:
    """Whether ``frequency`` names the note of ``target`` in some octave, its nearest semitone whole octaves off."""
    return round(semitones_between(frequency, target)) % OCTAVE_SEMITONES == 0


def nearest_semitone(frequency: float) -> int:
    """The equal-tempered semitone nearest ``frequency``, counted from A4 at 440 Hz.

    A pitch line is read note by note, and two frequencies nearest one semitone name one note.
    """
    return round(semitones_between(frequency, A4_FREQUENCY))


def line_semitones(line: PitchLine) -> List[Optional[int]]:
    """The semitone nearest each frame of ``line``, ``None`` where the line is silent."""
    return [None if frequency is None else nearest_semitone(frequency) for frequency in line]
