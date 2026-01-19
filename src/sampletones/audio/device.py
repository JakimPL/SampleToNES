from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.audio import DEFAULT_SAMPLE_RATE, SampleRate


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
    def default(cls) -> CurrentDevice:
        return cls(
            device_index=-1,
            name="",
            sample_rate=DEFAULT_SAMPLE_RATE,
            host_api=-1,
        )


class AudioDevice(BaseModel):
    """
    Model representing a sounddevice audio device.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(..., description="Device index")
    name: str = Field(..., description="Device name")
    is_input: bool = Field(..., description="Whether the device is an input device")
    is_output: bool = Field(..., description="Whether the device is an output device")
    is_default_input: bool = Field(..., description="Whether the device is the default input device")
    is_default_output: bool = Field(..., description="Whether the device is the default output device")
    default_sample_rate: SampleRate = Field(..., description="Default sample rate of the device")
    supported_sample_rates: List[SampleRate] = Field(
        ...,
        description="List of supported sample rates for the device",
    )
    host_api: int = Field(..., description="Host API index")
