from typing import Final, List, Literal, cast

SampleRate = Literal[8000, 16000, 22050, 44100, 48000, 96000, 192000]
SAMPLE_RATES: List[SampleRate] = cast(List[SampleRate], SampleRate.__args__)

DEFAULT_SAMPLE_RATE: Final[SampleRate] = 44100
MIN_SAMPLE_RATE: Final[SampleRate] = 8000
MAX_SAMPLE_RATE: Final[SampleRate] = 192000
