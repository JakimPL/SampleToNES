from __future__ import annotations

from pathlib import Path
from typing import List, Self

from pydantic import ConfigDict, Field

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.data import DataModel
from sampletones_core.data.metadata import Metadata
from sampletones_core.paths import CONFIG_PATH
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.serialization import load_json, save_json
from sampletones_shared.utils.system.paths import to_path
from sampletones_shared.utils.validation import validate_with_recovery

from .general import GeneralConfig
from .generation import GenerationConfig
from .library import InstructionsLibraryConfig


class Config(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    general: GeneralConfig = Field(
        default_factory=GeneralConfig,
        description="Base configuration for audio processing",
    )
    library: InstructionsLibraryConfig = Field(
        default_factory=InstructionsLibraryConfig,
        description="Configuration for the audio library",
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="Configuration for generation processes",
    )
    metadata: Metadata = Field(
        default_factory=Metadata.default,
        description="Application metadata",
    )

    @classmethod
    def default(cls) -> Self:
        if not CONFIG_PATH.exists():
            return cls()

        return cls.load(CONFIG_PATH)

    @classmethod
    def load(cls, path: Pathlike, fast: bool = False) -> Self:
        path = to_path(path)
        config_dict = load_json(path)
        if not isinstance(config_dict, dict):
            raise TypeError(f"Expected config file to contain a dict, got {type(config_dict)}")

        if fast:
            return cls.model_construct(**config_dict)

        return validate_with_recovery(cls, config_dict).model

    def save(self, path: Pathlike) -> None:
        path = to_path(path)
        config_dict = self.model_dump()
        save_json(path, config_dict)

    @property
    def max_workers(self) -> int:
        return self.general.max_workers

    @property
    def library_directory(self) -> Path:
        return Path(self.general.library_directory)

    @property
    def output_directory(self) -> Path:
        return Path(self.general.reconstructions_directory)

    @property
    def drive(self) -> float:
        return self.generation.drive

    @property
    def generators(self) -> List[GeneratorName]:
        return self.generation.generators.copy()

    @property
    def normalize(self) -> bool:
        return self.general.normalize

    @property
    def quantize(self) -> bool:
        return self.general.quantize

    @property
    def nes_frequency(self) -> int:
        return self.library.nes_frequency

    @property
    def sample_rate(self) -> int:
        return self.library.sample_rate

    @property
    def frame_length(self) -> int:
        return self.library.frame_length

    @property
    def transformation_gamma(self) -> int:
        return self.library.transformation_gamma
