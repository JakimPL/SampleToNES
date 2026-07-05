from typing import Dict

from pydantic import BaseModel, ConfigDict

from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_synthesis.voice.voice import Voice


class SynthConfig(BaseModel):
    """The named synthesizer voices of the integration suite and their shared noise seed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int
    voices: Dict[str, Voice]


def load_synth_config(path: Pathlike) -> SynthConfig:
    return load_yaml_model(path, SynthConfig)
