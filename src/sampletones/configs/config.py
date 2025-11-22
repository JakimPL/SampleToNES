from pathlib import Path
from types import ModuleType
from typing import List, Union

from pydantic import ConfigDict, Field

from sampletones.constants.enums import GeneratorName
from sampletones.constants.paths import CONFIG_PATH
from sampletones.data import DataModel
from sampletones.utils import load_json, save_json, to_path

from .general import GeneralConfig
from .generation import GenerationConfig
from .library import LibraryConfig


class Config(DataModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid", frozen=True)

    general: GeneralConfig = Field(default_factory=GeneralConfig, description="Base configuration for audio processing")
    library: LibraryConfig = Field(default_factory=LibraryConfig, description="Configuration for the audio library")
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig, description="Configuration for generation processes"
    )

    @classmethod
    def default(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()

        return cls.load(CONFIG_PATH)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Config":
        path = to_path(path)
        config_dict = load_json(path)
        return cls(**config_dict)

    def save(self, path: Union[str, Path]) -> None:
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
        return Path(self.general.output_directory)

    @property
    def mixer(self) -> float:
        return self.generation.mixer

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
    def change_rate(self) -> int:
        return self.library.change_rate

    @property
    def sample_rate(self) -> int:
        return self.library.sample_rate

    @property
    def frame_length(self) -> int:
        return self.library.frame_length

    @property
    def transformation_gamma(self) -> int:
        return self.library.transformation_gamma

    @classmethod
    def buffer_builder(cls) -> ModuleType:
        from schemas.configs import FBConfig

        return FBConfig

    @classmethod
    def buffer_reader(cls) -> type:
        from schemas.configs import FBConfig

        return FBConfig.FBConfig
