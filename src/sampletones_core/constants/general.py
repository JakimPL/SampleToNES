from typing import Final, Tuple

from .enums import PhaseAlignerName, SelectorName, SpectralDistance

# NES limits

DEFAULT_NES_FREQUENCY: Final[int] = 30  # half of NTSC frame rate
MIN_NES_FREQUENCY: Final[int] = 15
MAX_NES_FREQUENCY: Final[int] = 300

# Pitches and frequencies

APU_CLOCK: Final[float] = 1789773.0
LIMIT_MIN_PITCH: Final[int] = 24
MIN_PITCH: Final[int] = 33
MAX_PITCH: Final[int] = 119
LIMIT_MAX_PITCH: Final[int] = 127
PITCH_RANGE: Final[int] = MAX_PITCH - MIN_PITCH

MIN_FREQUENCY: Final[float] = APU_CLOCK / 0x8000
MAX_FREQUENCY: Final[float] = APU_CLOCK / 0x10

A4_FREQUENCY: Final[float] = 440.0
A4_PITCH: Final[int] = 69
NOTE_NAMES: Tuple[str, ...] = (
    "C-",
    "C#",
    "D-",
    "D#",
    "E-",
    "F-",
    "F#",
    "G-",
    "G#",
    "A-",
    "A#",
    "B-",
)

MIN_TRANSPOSE: Final[int] = -24
MAX_TRANSPOSE: Final[int] = 36

# Instruction parameters ranges

MIN_VOLUME: Final[int] = 1
MAX_VOLUME: Final[int] = 15
VOLUME_RANGE: Final[range] = range(0, MAX_VOLUME + 1)
MAX_DUTY_CYCLE: Final[int] = 3
SPECTRUM_FLOOR: Final[float] = (MIN_VOLUME / MAX_VOLUME) ** 2

# Audio import

NORMALIZE: Final[bool] = True
# Quantizing the input to QUANTIZATION_LEVELS is applied after peak-normalization,
# so it acts as a peak-relative gate that zeros everything below half a level
# (~-29.5 dB of the loudest sample). It does not improve matching, so it is off by
# default; the user can re-enable it for a deliberate lo-fi effect.
QUANTIZE: Final[bool] = False
QUANTIZATION_LEVELS: Final[int] = 32

# Matching input level: the normalization coefficient anchors to a robust level
# (a percentile of the per-frame peak amplitudes over frames audible relative to
# the global peak) rather than the single loudest sample, so a lone transient does
# not push the rest of the signal below the NES's matchable range.
COEFFICIENT_PERCENTILE: Final[float] = 90.0
COEFFICIENT_AUDIBILITY_FLOOR: Final[float] = 1e-3
# Floor on the reference level so a fully silent input does not divide by zero.
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
PERCEPTUAL_EXPONENT: Final[float] = 0.5

# Selection and continuity decoding

SELECTOR: Final[SelectorName] = SelectorName.VITERBI
DECODER_TOP_K: Final[int] = 8
TRANSITION_PITCH_WEIGHT: Final[float] = 0.03
TRANSITION_VOLUME_WEIGHT: Final[float] = 0.02
TRANSITION_TIMBRE_WEIGHT: Final[float] = 0.10
TRANSITION_ON_OFF_WEIGHT: Final[float] = 0.20

BATCH_SIZE: Final[int] = 512
MAX_WORKERS: Final[int] = 6

# Channel-specific constants

## Pulse channel

DUTY_CYCLES: Final[Tuple[float, ...]] = (0.125, 0.25, 0.5, 0.75)
DUTY_CYCLES_MAX_DEVIATION: Final[float] = 0.375

## Triangle channel

TRIANGLE_OFFSET: Final[float] = 0.5

## Noise channel

NOISE_PERIODS: Final[Tuple[int, ...]] = (
    4068,
    2034,
    1016,
    762,
    508,
    380,
    254,
    202,
    160,
    128,
    96,
    64,
    32,
    16,
    8,
    4,
)
NUM_PERIODS: Final[int] = len(NOISE_PERIODS)
MAX_PERIOD: Final[int] = NUM_PERIODS - 1

NOISE_SHORT_PERIOD: Final[float] = 93.0
NOISE_LONG_PERIOD: Final[float] = 32767.0
MAX_LFSR: Final[int] = 0x7FFF
MAX_LFSR_SHORT: Final[int] = 0x5D

# Mixer constants

DRIVE: Final[float] = 1.0
MAX_DRIVE: Final[float] = 5.0
MIXER_PULSE: Final[float] = 0.26395226395226395
MIXER_TRIANGLE: Final[float] = 0.2987012987012987
MIXER_NOISE: Final[float] = 0.1733941733941734
