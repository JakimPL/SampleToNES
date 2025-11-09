from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

from configs.config import Config as Configuration
from configs.library import LibraryConfig
from constants.enums import GeneratorClassName
from constants.general import LIBRARY_DIRECTORY
from ffts.window import Window
from library.data import LibraryData
from library.key import LibraryKey
from library.worker import LibraryWorker
from reconstructor.maps import GENERATOR_CLASS_MAP
from typehints.generators import GeneratorUnion
from typehints.instructions import InstructionUnion
from utils.parallelization.parallel import parallelize


def generate_library_data(
    instructions_ids: List[int],
    instructions: List[Tuple[GeneratorClassName, InstructionUnion]],
    config: LibraryConfig,
    window: Window,
    generators: Dict[GeneratorClassName, Any],
) -> LibraryData:
    worker = LibraryWorker(config=config, window=window, generators=generators)
    return worker(instructions, instructions_ids)


class Library(BaseModel):
    directory: str = Field(default=LIBRARY_DIRECTORY, description="Path to the FFT library directory")
    data: Dict[LibraryKey, LibraryData] = Field(default_factory=dict, description="FFT library data")

    def __getitem__(self, key: LibraryKey) -> LibraryData:
        return self.data[key]

    def create_key(self, config: Configuration, window: Window) -> LibraryKey:
        return LibraryKey.create(config.library, window)

    def get(self, config: Configuration, window: Window) -> LibraryData:
        key = self.create_key(config, window)
        if key not in self.data:
            if self.exists(key):
                self.load_data(key)
            else:
                self.update(config, window)

        return self.data[key]

    def exists(self, key: LibraryKey) -> bool:
        return self.get_path(key).exists()

    def purge(self) -> None:
        self.data.clear()

    def update(self, config: Configuration, window: Window, overwrite: bool = False) -> LibraryKey:
        key = self.create_key(config, window)
        if not overwrite and key in self.data:
            return key

        generators: Dict[GeneratorClassName, GeneratorUnion] = {
            name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP
        }

        instructions: List[Tuple[GeneratorClassName, InstructionUnion]] = [
            (generator.class_name(), instruction)
            for generator in generators.values()
            for instruction in generator.get_possible_instructions()
        ]

        instructions_ids = list(range(len(instructions)))
        if config.general.max_workers > 1:
            results = parallelize(
                generate_library_data,
                instructions_ids,
                max_workers=config.general.max_workers,
                instructions=instructions,
                config=config.library,
                window=window,
                generators=generators,
            )

            library_data = LibraryData.merge(results)
        else:
            worker = LibraryWorker(config=config.library, window=window, generators=generators)
            library_data = worker(instructions, instructions_ids, show_progress=True)

        self.save_data(key, library_data)
        return key

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

    class Config:
        arbitrary_types_allowed = True
