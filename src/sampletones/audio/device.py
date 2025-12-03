from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import DEFAULT_SAMPLE_RATE

SampleRate = Literal[22050, 44100, 48000, 96000, 192000]
BitDepth = Literal[8, 16, 24, 32]

SAMPLE_RATES = SampleRate.__args__
BIT_DEPTHS = BitDepth.__args__
DEFAULT_BIT_DEPTH = 32


class CurrentDevice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    device_index: int = Field(..., description="Device index")
    name: str = Field(..., description="Device name")
    sample_rate: SampleRate = Field(..., description="Sample rate")
    bit_depth: BitDepth = Field(..., description="Bit depth")

    @classmethod
    def default(cls) -> "CurrentDevice":
        return cls(
            device_index=-1,
            name="",
            sample_rate=DEFAULT_SAMPLE_RATE,
            bit_depth=DEFAULT_BIT_DEPTH,
        )


class AudioDevice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int
    name: str
    is_input: bool
    is_output: bool
    is_default_input: bool
    is_default_output: bool
    default_sample_rate: SampleRate
    supported_sample_rates: List[SampleRate]
    supported_bit_depths: List[BitDepth]
