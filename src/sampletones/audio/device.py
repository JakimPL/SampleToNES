from typing import List, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import DEFAULT_SAMPLE_RATE

SampleRate = Literal[22050, 44100, 48000, 96000, 192000]
SAMPLE_RATES: List[SampleRate] = cast(List[SampleRate], SampleRate.__args__)


class CurrentDevice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    device_index: int = Field(..., description="Device index")
    name: str = Field(..., description="Device name")
    sample_rate: SampleRate = Field(..., description="Sample rate")

    @classmethod
    def default(cls) -> "CurrentDevice":
        return cls(
            device_index=-1,
            name="",
            sample_rate=DEFAULT_SAMPLE_RATE,
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
