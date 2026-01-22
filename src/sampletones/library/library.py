from __future__ import annotations

from pathlib import Path
from typing import Dict, ItemsView, KeysView, Optional, Union, ValuesView

from pydantic import BaseModel, ConfigDict, Field

from sampletones.configs import Config
from sampletones.constants.paths import LIBRARY_DIRECTORY
from sampletones.fft import Window
from sampletones.utils.logger import logger

from .data import InstructionLibraryData
from .key import InstructionLibraryKey


class InstructionLibrary(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    directory: str = Field(default=str(LIBRARY_DIRECTORY), description="Path to the FFT library directory", frozen=True)
    data: Dict[InstructionLibraryKey, InstructionLibraryData] = Field(
        default_factory=dict, description="FFT library data"
    )

    def __getitem__(self, key: InstructionLibraryKey) -> InstructionLibraryData:
        return self.data[key]

    @classmethod
    def from_config(cls, config: Config) -> InstructionLibrary:
        return cls(directory=str(config.general.library_directory))

    def create_key(self, config: Config, window: Window) -> InstructionLibraryKey:
        return InstructionLibraryKey.create(config.library, window)

    def get(self, config: Config, window: Optional[Window] = None) -> Optional[InstructionLibraryData]:
        if window is None:
            window = Window.from_config(config)

        key = self.create_key(config, window)
        if key in self.data:
            return self.data[key]

        if self.exists(key):
            self.load_data(key)
            return self.data[key]

        logger.warning(f"Library data for key {key} does not exist")
        return None

    def exists(self, config_or_key: Union[Config, InstructionLibraryKey]) -> bool:
        if isinstance(config_or_key, Config):
            key = self.create_key(config_or_key, Window.from_config(config_or_key))
        else:
            key = config_or_key

        return self.get_path(key).exists()

    def purge(self) -> None:
        self.data.clear()

    def keys(self) -> KeysView[InstructionLibraryKey]:
        return self.data.keys()

    def items(self) -> ItemsView[InstructionLibraryKey, InstructionLibraryData]:
        return self.data.items()

    def values(self) -> ValuesView[InstructionLibraryData]:
        return self.data.values()

    def get_path(self, key: InstructionLibraryKey) -> Path:
        return Path(self.directory) / key.filename

    def save_data(self, key: InstructionLibraryKey, library_data: InstructionLibraryData) -> None:
        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.data[key] = library_data
        library_data.save(path)

    def load_data(self, key: InstructionLibraryKey) -> None:
        path = self.get_path(key)
        library_data = InstructionLibraryData.load(path)
        self.data[key] = library_data
