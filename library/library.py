from dis import Instruction
from pathlib import Path
from typing import Any, Dict, List, Self, Tuple

import msgpack
from pydantic import BaseModel, Field, field_serializer

from config import Config as Config
from constants import LIBRARY_PATH
from ffts.window import Window
from library.data import LibraryData
from library.key import LibraryKey
from library.worker import LibraryWorker
from reconstructor.maps import GENERATOR_CLASS_MAP
from typehints.general import GeneratorClassName
from utils.common import dump
from utils.parallel import parallelize


def generate_library_data(
    instructions_ids: List[int],
    instructions: Tuple[GeneratorClassName, Instruction],
    config: Config,
    window: Window,
    generators: Dict[str, Any],
) -> Dict[int, LibraryData]:
    worker = LibraryWorker(config=config, window=window, generators=generators)
    return worker(instructions, instructions_ids)


class Library(BaseModel):
    path: str = Field(LIBRARY_PATH, description="Path to the FFT library file")
    data: Dict[LibraryKey, LibraryData] = Field(..., default_factory=dict, description="FFT library data")

    def __getitem__(self, key: LibraryKey) -> LibraryData:
        return self.data[key]

    def get(self, config: Config, window: Window) -> LibraryData:
        key = LibraryKey.create(config, window)
        if key not in self.data:
            self.update(config, window)

        return self.data[key]

    def update(self, config: Config, window: Window, overwrite: bool = False) -> LibraryKey:
        key = LibraryKey.create(config, window)
        if not overwrite and key in self.data:
            return key

        generators = {name: GENERATOR_CLASS_MAP[name](config, name) for name in GENERATOR_CLASS_MAP}
        instructions = [
            (generator.class_name(), instruction)
            for generator in generators.values()
            for instruction in generator.get_possible_instructions()
        ]

        instructions_ids = list(range(len(instructions)))
        if config.max_workers > 1:
            library_data = parallelize(
                generate_library_data,
                instructions_ids,
                max_workers=config.max_workers,
                instructions=instructions,
                config=config,
                window=window,
                generators=generators,
            )

            library_data = LibraryData.merge(library_data)
        else:
            worker = LibraryWorker(config=config, window=window, generators=generators)
            library_data = worker(instructions, instructions_ids, show_progress=True)

        self.data[key] = library_data
        self._save()
        return key

    def keys(self):
        return self.data.keys()

    def items(self):
        return self.data.items()

    def values(self):
        return self.data.values()

    def _save(self):
        dump = self.model_dump()
        binary = msgpack.packb(dump)
        path_object = Path(self.path)
        path_object.parent.mkdir(parents=True, exist_ok=True)
        with open(path_object, "wb") as file:
            file.write(binary)

    def _load(self):
        path_object = Path(self.path)
        with open(path_object, "rb") as file:
            binary = file.read()

        dump = msgpack.unpackb(binary)
        self.path = dump["path"]
        self.data = {LibraryKey.deserialize(key): LibraryData.deserialize(data) for key, data in dump["data"].items()}

    @field_serializer("data")
    def serialize_data(self, data: Dict[LibraryKey, LibraryData], _info) -> Dict[str, Any]:
        return {dump(k.model_dump()): v.model_dump() for k, v in data.items()}

    @classmethod
    def load(cls, path: str = LIBRARY_PATH) -> Self:
        library = cls(path=path)
        if Path(path).exists():
            library._load()

        return library

    class Config:
        arbitrary_types_allowed = True
