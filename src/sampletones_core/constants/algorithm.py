from typing import Final

from .enums import PhaseAlignerName, SelectorName, SpectralDistance
from .general import MAX_VOLUME, MIN_VOLUME

# Matching floors

SPECTRUM_FLOOR: Final[float] = (MIN_VOLUME / MAX_VOLUME) ** 2
TEMPORAL_LEVEL_FLOOR: Final[float] = MIN_VOLUME / MAX_VOLUME

# Input preprocessing

NORMALIZE: Final[bool] = True
QUANTIZE: Final[bool] = False
QUANTIZATION_LEVELS: Final[int] = 32

# Working level

COEFFICIENT_PERCENTILE: Final[float] = 90.0
COEFFICIENT_AUDIBILITY_FLOOR: Final[float] = 1e-3
MINIMUM_AUDIO_LEVEL: Final[float] = 1e-12

# Library creation

MIN_SAMPLE_LENGTH: Final[float] = 0.05
MAX_SAMPLE_LENGTH: Final[float] = 1.0
LIBRARY_PHASES_PER_SAMPLE: Final[int] = 100

# Calculation methods

TRANSFORMATION_GAMMA: Final[int] = 0
MAX_TRANSFORMATION_GAMMA: Final[int] = 100
FIND_BEST_PHASE: Final[bool] = True
FAST_DIFFERENCE: Final[bool] = False
PHASE_ALIGNER: Final[PhaseAlignerName] = PhaseAlignerName.CROSS_CORRELATION

RESET_PHASE: Final[bool] = False
FINAL_REGENERATION: Final[bool] = True
SPECTRAL_LOSS_WEIGHT: Final[float] = 0.80
TEMPORAL_LOSS_WEIGHT: Final[float] = 0.20

SPECTRAL_DISTANCE: Final[SpectralDistance] = SpectralDistance.BETA_DIVERGENCE
DIVERGENCE_BETA: Final[float] = 1.0
PERCEPTUAL_EXPONENT: Final[float] = 1.0

# Selection and continuity decoding

SELECTOR: Final[SelectorName] = SelectorName.VITERBI
DECODER_TOP_K: Final[int] = 8
TRANSITION_PITCH_WEIGHT: Final[float] = 0.03
TRANSITION_VOLUME_WEIGHT: Final[float] = 0.02
TRANSITION_TIMBRE_WEIGHT: Final[float] = 0.10
TRANSITION_ON_OFF_WEIGHT: Final[float] = 0.20

# Mixer drive

DRIVE: Final[float] = 1.0
MAX_DRIVE: Final[float] = 5.0

# Execution

MAX_WORKERS: Final[int] = 6
