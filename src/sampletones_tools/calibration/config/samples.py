from typing import List, Self

from pydantic import BaseModel, ConfigDict, Field, NonNegativeFloat, PositiveFloat, model_validator

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.calibration.paths import SAMPLES_CONFIG_PATH


class SampleReference(BaseModel):
    """A recording the benchmark downloads from where it is published, and the window of it heard.

    Attributes:
        name: The name its files are written under.
        url: Where the recording is published.
        file_name: The name the download is kept under.
        sha256: The download's checksum, which a fetched file must match.
        start_seconds: Where the window heard starts.
        end_seconds: Where it ends.
        license: The license the recording is published under.
        attribution: The credit the license asks for.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    url: str
    file_name: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    start_seconds: NonNegativeFloat
    end_seconds: PositiveFloat
    license: str
    attribution: str

    @model_validator(mode="after")
    def _validate_window(self) -> Self:
        if self.end_seconds <= self.start_seconds:
            raise ValueError(f"The window of {self.name!r} must end after it starts")

        return self


class SamplesConfig(BaseModel):
    """The recordings the benchmark keeps for listening, downloaded by reference.

    Attributes:
        user_agent: The name the downloads introduce themselves by.
        pause_seconds: The pause between two downloads, which keeps the publishers' limits.
        samples: The recordings.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    user_agent: str
    pause_seconds: NonNegativeFloat
    samples: List[SampleReference] = Field(min_length=1)

    @classmethod
    def load(cls) -> Self:
        """The references the package ships."""
        return load_yaml_model(SAMPLES_CONFIG_PATH, cls)
