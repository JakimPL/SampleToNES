from typing import Final

from sampletones_shared.constants.music import OCTAVE_SEMITONES

from .general import MIN_FREQUENCY

BINS_PER_OCTAVE: Final[int] = OCTAVE_SEMITONES
CQT_CUTOFF_FREQUENCY: Final[float] = MIN_FREQUENCY

CQT_REFERENCE_CONTEXT_FACTOR: Final[int] = 3
CQT_REFERENCE_COLUMNS: Final[int] = 8

# Glasberg-Moore auditory filter bandwidth: ERB(f) = 24.7 * (1 + 4.37 * f / 1000)

ERB_MINIMUM_BANDWIDTH: Final[float] = 24.7
ERB_FREQUENCY_FACTOR: Final[float] = 4.37e-3
