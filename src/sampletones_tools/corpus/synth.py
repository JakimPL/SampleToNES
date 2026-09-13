from typing import Dict, Self

from pydantic import BaseModel, ConfigDict

from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.paths import SYNTH_CONFIG_PATH
from sampletones_tools.synthesis.voice.voice import Voice


class SynthConfig(BaseModel):
    """The named synthesizer voices the corpus is rendered from and their shared noise seed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: int
    voices: Dict[str, Voice]

    @classmethod
    def load(cls) -> Self:
        """The voices the package ships."""
        return load_yaml_model(SYNTH_CONFIG_PATH, cls)
