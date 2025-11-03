from pathlib import Path
from typing import Dict, List, Optional, Tuple

from anytree import Node

from browser.tree.tree import Tree
from configs.config import Config
from constants.browser import (
    NOD_LABEL_LIBRARIES,
    NOD_LABEL_NOT_LOADED,
    NOD_TYPE_GENERATOR,
    NOD_TYPE_GROUP,
    NOD_TYPE_INSTRUCTION,
    NOD_TYPE_LIBRARY,
    NOD_TYPE_LIBRARY_PLACEHOLDER,
)
from constants.enums import GeneratorClassName, LibraryGeneratorName
from constants.general import LIBRARY_DIRECTORY, NOISE_PERIODS
from ffts.window import Window
from instructions.instruction import Instruction
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from library.data import LibraryData, LibraryFragment
from library.key import LibraryKey
from library.library import Library
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from utils.frequencies import pitch_to_name


class LibraryManager:
    def __init__(self, library_directory: str = LIBRARY_DIRECTORY) -> None:
        self.library = Library(directory=library_directory)
        self.library_files: Dict[str, str] = {}
        self.current_library_key: Optional[LibraryKey] = None
        self.tree = Tree()

    def set_library_directory(self, directory: str) -> None:
        self.library.directory = directory
        self.gather_available_libraries()

    def gather_available_libraries(self) -> Dict[str, str]:
        library_directory = Path(self.library.directory)
        if not library_directory.exists():
            self.library_files.clear()
            self._rebuild_tree()
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
        self._rebuild_tree()
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
        for generator_name in LibraryGeneratorName:
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

        instructions: Dict[str, List[Tuple[Instruction, LibraryFragment]]] = {}
        sorted_generator_data = dict(sorted(generator_data.items(), key=lambda item: item[0]))
        for instruction, fragment in sorted_generator_data.items():
            if not instruction.on:
                continue

            if isinstance(instruction, (PulseInstruction, TriangleInstruction)):
                grouping_key = pitch_to_name(instruction.pitch)
            elif isinstance(instruction, NoiseInstruction):
                grouping_key = f"p{NOISE_PERIODS[instruction.period]}"
            else:
                raise TypeError(f"Unsupported instruction type {type(instruction)} for grouping")

            if grouping_key not in instructions:
                instructions[grouping_key] = []

            instructions[grouping_key].append((instruction, fragment))

        return instructions

    def _rebuild_tree(self) -> None:
        root = Node(NOD_LABEL_LIBRARIES)

        for display_name in sorted(self.library_files.keys()):
            self._build_library_node(display_name, root)

        self.tree.set_root(root)

    def _build_library_node(self, display_name: str, parent: Node) -> Node:
        library_node = Node(display_name, parent=parent, display_name=display_name, node_type=NOD_TYPE_LIBRARY)

        if self.is_library_loaded(display_name):
            self._build_generator_nodes(display_name, library_node)
        else:
            self._create_placeholder_node(display_name, library_node)

        return library_node

    def _create_placeholder_node(self, display_name: str, parent: Node) -> Node:
        return Node(
            NOD_LABEL_NOT_LOADED, parent=parent, display_name=display_name, node_type=NOD_TYPE_LIBRARY_PLACEHOLDER
        )

    def _build_generator_nodes(self, display_name: str, parent: Node) -> None:
        for generator_name in LibraryGeneratorName:
            grouped_instructions = self.get_library_instructions_by_generator(display_name, generator_name)

            if not grouped_instructions:
                continue

            generator_node = Node(
                generator_name.value.capitalize(),
                parent=parent,
                display_name=display_name,
                generator_name=generator_name,
                node_type=NOD_TYPE_GENERATOR,
            )

            self._build_group_nodes(display_name, generator_name, grouped_instructions, generator_node)

    def _build_group_nodes(
        self,
        display_name: str,
        generator_name: LibraryGeneratorName,
        grouped_instructions: Dict[str, List[Tuple]],
        parent: Node,
    ) -> None:
        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)

        for group_key, instructions in grouped_instructions.items():
            group_label = f"{group_key} ({len(instructions)} item(s))"
            group_node = Node(
                group_label,
                parent=parent,
                display_name=display_name,
                generator_name=generator_name,
                group_key=group_key,
                node_type=NOD_TYPE_GROUP,
            )

            for instruction, fragment in instructions:
                Node(
                    instruction.name,
                    parent=group_node,
                    display_name=display_name,
                    generator_name=generator_name,
                    generator_class_name=generator_class_name,
                    instruction=instruction,
                    fragment=fragment,
                    node_type=NOD_TYPE_INSTRUCTION,
                )

    def refresh_library_node(self, display_name: str) -> None:
        if not self.tree.root:
            return

        library_node = self.tree.find_node(
            lambda node: getattr(node, "node_type", None) == NOD_TYPE_LIBRARY and node.name == display_name
        )

        if library_node:
            for child in list(library_node.children):
                child.parent = None

            if self.is_library_loaded(display_name):
                self._build_generator_nodes(display_name, library_node)
            else:
                self._create_placeholder_node(display_name, library_node)
