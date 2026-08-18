from __future__ import annotations

from pathlib import Path
from typing import Dict, ItemsView, KeysView, Optional, Self, Union, ValuesView

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.configs import Config
from sampletones_core.fft import Window
from sampletones_shared.logger import logger
from sampletones_shared.paths.user import LIBRARY_DIRECTORY

from .data import InstructionLibraryData
from .key import InstructionLibraryKey


class InstructionLibrary(BaseModel):
    """
    A cache of per-configuration instruction libraries, backed by files on disk.

    Reconstruction matches audio against a library of pre-rendered instruction
    features. Which library applies depends on the analysis settings, so this class
    keys each :class:`InstructionLibraryData` by an :class:`InstructionLibraryKey`
    derived from the configuration and analysis window. Requested data is served from
    the in-memory cache, loaded from disk on first use, and a saved library is written
    back under the library directory.

    Attributes:
        directory: Root directory holding the library files.
        data: The in-memory cache of loaded libraries, keyed by configuration.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    directory: str = Field(
        default=str(LIBRARY_DIRECTORY),
        description="Root directory holding the instruction library files.",
        frozen=True,
    )
    data: Dict[InstructionLibraryKey, InstructionLibraryData] = Field(
        default_factory=dict,
        description="Cached instruction library data, keyed by configuration.",
    )

    def __getitem__(self, key: InstructionLibraryKey) -> InstructionLibraryData:
        return self.data[key]

    @classmethod
    def from_config(cls, config: Config) -> Self:
        """Builds a library rooted at the directory named in the configuration.

        Args:
            config: Configuration whose ``general.library_directory`` locates the files.

        Returns:
            Self: A library that reads from and writes to that directory.
        """
        return cls(directory=str(config.general.library_directory))

    def create_key(self, config: Config, window: Window) -> InstructionLibraryKey:
        """Builds the cache key for a configuration and analysis window.

        Args:
            config: Configuration whose library settings identify the library.
            window: The analysis window the library was built for.

        Returns:
            InstructionLibraryKey: The key locating this configuration's library.
        """
        return InstructionLibraryKey.create(config.library, window)

    def get(self, config: Config, window: Optional[Window] = None) -> Optional[InstructionLibraryData]:
        """Returns the library data for a configuration, loading it if needed.

        Serves the data from the in-memory cache, falling back to loading it from disk
        when a file exists for the key.

        Args:
            config: Configuration selecting which library to return.
            window: The analysis window; taken from ``config`` when omitted.

        Returns:
            Optional[InstructionLibraryData]: The library data, or ``None`` when no
                library exists for the configuration.
        """
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
        """Reports whether a library file exists on disk for the given key.

        Args:
            config_or_key: A configuration (whose key is derived) or a key directly.

        Returns:
            bool: True when the corresponding library file is present.
        """
        if isinstance(config_or_key, Config):
            key = self.create_key(config_or_key, Window.from_config(config_or_key))
        else:
            key = config_or_key

        return self.get_path(key).exists()

    def purge(self) -> None:
        """Empties the in-memory cache, so the next request reloads from disk."""
        self.data.clear()

    def keys(self) -> KeysView[InstructionLibraryKey]:
        return self.data.keys()

    def items(self) -> ItemsView[InstructionLibraryKey, InstructionLibraryData]:
        return self.data.items()

    def values(self) -> ValuesView[InstructionLibraryData]:
        return self.data.values()

    def get_path(self, key: InstructionLibraryKey) -> Path:
        """The file path a library key maps to under the library directory.

        Args:
            key: The key identifying the library.

        Returns:
            Path: The path to that library's file.
        """
        return Path(self.directory) / key.filename

    def save_data(self, key: InstructionLibraryKey, library_data: InstructionLibraryData) -> None:
        """Caches a library and writes it to its file on disk.

        Args:
            key: The key identifying the library.
            library_data: The library to cache and persist.
        """
        path = self.get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.data[key] = library_data
        library_data.save(path)

    def load_data(self, key: InstructionLibraryKey) -> None:
        """Loads a library from its file on disk into the cache.

        Args:
            key: The key identifying the library to load.
        """
        path = self.get_path(key)
        library_data = InstructionLibraryData.load(path)
        self.data[key] = library_data
