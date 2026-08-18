from typing import Literal, Self, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sampletones_core.constants.audio import MAX_SAMPLE_RATE, MIN_SAMPLE_RATE

from .bitrate import default_mp3_bitrate, mp3_bitrates
from .capability import FormatCapability, capability_of
from .format import DEFAULT_AUDIO_DEPTH, AudioDepth, AudioFormat


class AudioOutputSpecBase(BaseModel):
    """What every request to write audio states, whatever the container.

    The rate is checked against the format's capability on construction, so a specification that
    exists is one the encoder accepts.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    audio_format: AudioFormat = Field(..., description="The container the audio is written into.")
    sample_rate: int = Field(
        ...,
        ge=MIN_SAMPLE_RATE,
        le=MAX_SAMPLE_RATE,
        description="The samples the written audio holds each second.",
    )

    @property
    def capability(self) -> FormatCapability:
        return capability_of(self.audio_format)

    @property
    def extension(self) -> str:
        return self.capability.extension

    @model_validator(mode="after")
    def _validate_sample_rate(self) -> Self:
        if not self.capability.supports_sample_rate(self.sample_rate):
            raise ValueError(f"{self.audio_format} does not encode at {self.sample_rate} Hz")

        return self


class WaveOutputSpec(AudioOutputSpecBase):
    """A WAV file, which stores each sample at a chosen depth."""

    audio_format: Literal[AudioFormat.WAVE] = AudioFormat.WAVE
    depth: AudioDepth = Field(
        default=DEFAULT_AUDIO_DEPTH,
        description="The form each stored sample takes.",
    )

    @model_validator(mode="after")
    def _validate_depth(self) -> Self:
        if not self.capability.supports_depth(self.depth):
            raise ValueError(f"WAV does not store samples as {self.depth}")

        return self


class Mp3OutputSpec(AudioOutputSpecBase):
    """An MP3 file, which encodes to a chosen bitrate rather than storing samples.

    The bitrates on offer depend on the sample rate, since each MPEG audio version defines its own
    ladder, so the pair is validated together.
    """

    audio_format: Literal[AudioFormat.MP3] = AudioFormat.MP3
    bitrate: int = Field(..., description="The kilobits the encoded audio holds each second.")

    @classmethod
    def at(cls, sample_rate: int) -> Self:
        """A specification at ``sample_rate`` and the bitrate a render starts at there."""
        return cls(sample_rate=sample_rate, bitrate=default_mp3_bitrate(sample_rate))

    @model_validator(mode="after")
    def _validate_bitrate(self) -> Self:
        if self.bitrate not in mp3_bitrates(self.sample_rate):
            raise ValueError(f"MP3 at {self.sample_rate} Hz does not encode at {self.bitrate} kbps")

        return self


AudioOutputSpec = Union[WaveOutputSpec, Mp3OutputSpec]
