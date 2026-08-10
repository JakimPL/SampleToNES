from __future__ import annotations

from typing import List, Self

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.audio import DEFAULT_SAMPLE_RATE, SampleRate


class CurrentDevice(BaseModel):
    """
    Model representing the current audio device configuration.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    device_index: int = Field(..., description="Device index")
    name: str = Field(..., description="Device name")
    sample_rate: SampleRate = Field(..., description="Sample rate")
    host_api: int = Field(..., description="Host API index")

    @classmethod
    def default(cls) -> Self:
        return cls(
            device_index=-1,
            name="",
            sample_rate=DEFAULT_SAMPLE_RATE,
            host_api=-1,
        )


class AudioDevice(BaseModel):
    """
    Model representing an audio device available for output selection.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(..., description="Device index")
    name: str = Field(..., description="Device name")
    default_sample_rate: SampleRate = Field(..., description="Default sample rate of the device")
    supported_sample_rates: List[SampleRate] = Field(..., description="List of supported sample rates for the device")
    host_api: int = Field(..., description="Host API index")
