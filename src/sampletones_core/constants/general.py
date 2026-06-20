from typing import Final, Tuple

# NES limits

DEFAULT_NES_FREQUENCY: Final[int] = 60  # NTSC frame rate
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

# Audio import

NORMALIZE: Final[bool] = True
QUANTIZE: Final[bool] = True
QUANTIZATION_LEVELS: Final[int] = 32

# Library creation

MIN_SAMPLE_LENGTH: Final[float] = 0.05
MAX_SAMPLE_LENGTH: Final[float] = 1.0
LIBRARY_PHASES_PER_SAMPLE: Final[int] = 100

# Calculation methods

TRANSFORMATION_GAMMA: Final[int] = 50
MAX_TRANSFORMATION_GAMMA: Final[int] = 100
FIND_BEST_PHASE: Final[bool] = True
FAST_DIFFERENCE: Final[bool] = False

RESET_PHASE: Final[bool] = False
FINAL_REGENERATION: Final[bool] = True
SPECTRAL_LOSS_WEIGHT: Final[float] = 0.80
TEMPORAL_LOSS_WEIGHT: Final[float] = 0.20

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

DRIVE: Final[float] = 1.8
MAX_DRIVE: Final[float] = 5.0
MIXER_PULSE: Final[float] = 0.26395226395226395
MIXER_TRIANGLE: Final[float] = 0.2987012987012987
MIXER_NOISE: Final[float] = 0.1733941733941734
