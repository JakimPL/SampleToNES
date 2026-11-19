from typing import Annotated, Final, List, Literal, cast, get_args

from pydantic import Field

SampleRate = Literal[8000, 16000, 22050, 44100, 48000, 96000, 192000]
SAMPLE_RATES: Final[List[SampleRate]] = cast(List[SampleRate], get_args(SampleRate))

BufferSize = Literal[64, 128, 256, 512, 1024, 2048, 4096, 8192]
BUFFER_SIZES: Final[List[BufferSize]] = cast(List[BufferSize], get_args(BufferSize))

DEFAULT_BUFFER_SIZE: Final[BufferSize] = 1024
DEFAULT_SAMPLE_RATE: Final[SampleRate] = 44100
MIN_SAMPLE_RATE: Final[SampleRate] = 8000
MAX_SAMPLE_RATE: Final[SampleRate] = 192000
AcceptedSampleRate = Annotated[int, Field(ge=MIN_SAMPLE_RATE, le=MAX_SAMPLE_RATE)]

START_OF_AUDIO: Final[int] = 0
