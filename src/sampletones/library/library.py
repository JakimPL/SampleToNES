from pathlib import Path
from typing import Dict, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones.configs import Config
from sampletones.constants.paths import LIBRARY_DIRECTORY
from sampletones.ffts import Window
from sampletones.utils import logger

from .data import LibraryData
from .key import LibraryKey


class Library(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    directory: str = Field(default=str(LIBRARY_DIRECTORY), description="Path to the FFT library directory", frozen=True)
    data: Dict[LibraryKey, LibraryData] = Field(default_factory=dict, description="FFT library data")

    def __getitem__(self, key: LibraryKey) -> LibraryData:
        return self.data[key]

    @classmethod
    def from_config(cls, config: Config) -> "Library":
        return cls(directory=str(config.general.library_directory))

    def create_key(self, config: Config, window: Window) -> LibraryKey:
        return LibraryKey.create(config.library, window)

    def get(self, config: Config, window: Optional[Window] = None) -> Optional[LibraryData]:
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

    def exists(self, config_or_key: Union[Config, LibraryKey]) -> bool:
        if isinstance(config_or_key, Config):
            key = self.create_key(config_or_key, Window.from_config(config_or_key))
        else:
            key = config_or_key

        return self.get_path(key).exists()

    def purge(self) -> None:
        self.data.clear()

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def get_path(self, key: LibraryKey) -> Path:
        return Path(self.directory) / key.filename

    def save_data(self, key: LibraryKey, library_data: LibraryData) -> None:
        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.data[key] = library_data
        library_data.save(path)

    def load_data(self, key: LibraryKey) -> None:
        path = self.get_path(key)
        library_data = LibraryData.load(path)
        self.data[key] = library_data
