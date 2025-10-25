from pathlib import Path
from typing import Dict, List, Optional, Tuple

from configs.config import Config
from constants import LIBRARY_DIRECTORY, NOISE_PERIODS
from ffts.window import Window
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from library.data import LibraryData
from library.key import LibraryKey
from library.library import Library
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from typehints.general import (
    LIBRARY_GENERATOR_NAMES,
    GeneratorClassName,
    LibraryGeneratorName,
)
from utils.frequencies import pitch_to_name


class LibraryManager:
    def __init__(self, library_directory: str = LIBRARY_DIRECTORY) -> None:
        self.library = Library(directory=library_directory)
        self.library_files: Dict[str, str] = {}
        self.current_library_key: Optional[LibraryKey] = None

    def set_library_directory(self, directory: str) -> None:
        self.library.directory = directory

    def gather_available_libraries(self) -> Dict[str, str]:
        library_directory = Path(self.library.directory)
        if not library_directory.exists():
            self.library_files.clear()
            return {}

        new_library_files = {}
        for file_path in library_directory.iterdir():
            if file_path.is_file() and file_path.suffix == ".dat" and self._is_library_file(file_path.stem):
                display_name = self._get_display_name(file_path.stem)
                new_library_files[display_name] = file_path.stem

        removed_libraries = set(self.library_files.keys()) - set(new_library_files.keys())
        for removed_library in removed_libraries:
            key = self._get_library_key_from_display_name(removed_library)
            if key and key in self.library.data:
                del self.library.data[key]

        self.library_files = new_library_files
        return self.library_files

    def get_available_libraries(self) -> Dict[str, str]:
        return self.library_files.copy()

    def is_library_loaded(self, display_name: str) -> bool:
        key = self._get_library_key_from_display_name(display_name)
        return key is not None and key in self.library.data

    def load_library(self, display_name: str) -> bool:
        if display_name not in self.library_files:
            return False

        if self.is_library_loaded(display_name):
            return True

        library_key = self._get_library_key_from_display_name(display_name)
        if library_key:
            self.library.load_data(library_key)
            return True
        return False

    def get_library_data(self, display_name: str) -> Optional[LibraryData]:
        key = self._get_library_key_from_display_name(display_name)
        return self.library.data.get(key) if key else None

    def get_library_instructions_by_generator(
        self, display_name: str, generator_name: LibraryGeneratorName
    ) -> Dict[str, List[Tuple]]:
        library_data = self.get_library_data(display_name)
        if not library_data:
            return {}

        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        if not generator_class_name:
            return {}

        return self._parse_instructions_by_generator(library_data, generator_class_name)

    def get_all_generator_instructions(self, display_name: str) -> Dict[LibraryGeneratorName, Dict[str, List[Tuple]]]:
        result = {}
        for generator_name in LIBRARY_GENERATOR_NAMES:
            instructions = self.get_library_instructions_by_generator(display_name, generator_name)
            if instructions:
                result[generator_name] = instructions
        return result

    def sync_with_config_key(self, config_key: LibraryKey) -> Optional[str]:
        matching_display_name = self._get_display_name_from_key(config_key)
        if matching_display_name in self.library_files:
            self.current_library_key = config_key
            return matching_display_name
        return None

    def get_library_key_for_config_update(self, display_name: str) -> Optional[LibraryKey]:
        return self._get_library_key_from_display_name(display_name)

    def library_exists_for_key(self, key: LibraryKey) -> bool:
        return self.library.exists(key)

    def generate_library(self, config: Config, window: Window, overwrite: bool = False) -> LibraryKey:
        self.library.directory = config.general.library_directory
        return self.library.update(config, window, overwrite=overwrite)

    def clear_all_libraries(self) -> None:
        self.library.purge()
        self.library_files.clear()
        self.current_library_key = None

    def _is_library_file(self, file_name: str) -> bool:
        file_parts = file_name.split("_")
        if len(file_parts) < 4:
            return False
        if not file_parts[0] == "sr" or not file_parts[1].isdigit():
            return False
        if not file_parts[2] == "fl" or not file_parts[3].isdigit():
            return False
        return len(file_parts) >= 6

    def _create_key_from_file_name(self, file_name: str) -> LibraryKey:
        file_parts = file_name.split("_")
        if len(file_parts) < 8:
            raise ValueError(f"Invalid library file name format: {file_name}")

        sample_rate = int(file_parts[1])
        frame_length = int(file_parts[3])
        window_size = int(file_parts[5])
        config_hash = file_parts[7]

        return LibraryKey(
            sample_rate=sample_rate, frame_length=frame_length, window_size=window_size, config_hash=config_hash
        )

    def _get_display_name_from_key(self, key: LibraryKey) -> str:
        sample_rate = key.sample_rate
        change_rate = round(sample_rate / key.frame_length)
        hash_part = key.config_hash[:7]
        return f"{sample_rate}_{change_rate}_{hash_part}"

    def _get_display_name(self, file_name: str) -> str:
        key = self._create_key_from_file_name(file_name)
        return self._get_display_name_from_key(key)

    def _get_library_key_from_display_name(self, display_name: str) -> Optional[LibraryKey]:
        if display_name not in self.library_files:
            return None
        full_file_name = self.library_files[display_name]
        return self._create_key_from_file_name(full_file_name)

    def _parse_instructions_by_generator(
        self, library_data: LibraryData, generator_class_name: GeneratorClassName
    ) -> Dict[str, List[Tuple]]:
        generator_data = library_data.filter(generator_class_name)
        if not generator_data:
            return {}

        grouped_instructions = {}

        for instruction, fragment in generator_data.items():
            if not instruction.on:
                continue

            if isinstance(instruction, (PulseInstruction, TriangleInstruction)):
                grouping_key = pitch_to_name(instruction.pitch)
            elif isinstance(instruction, NoiseInstruction):
                grouping_key = f"p{NOISE_PERIODS[instruction.period]}"
            else:
                grouping_key = "Other"

            if grouping_key not in grouped_instructions:
                grouped_instructions[grouping_key] = []

            grouped_instructions[grouping_key].append((instruction, fragment))

        return grouped_instructions
