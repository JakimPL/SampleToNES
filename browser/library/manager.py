from pathlib import Path
from typing import Dict, List, Optional, Tuple

from browser.tree.node import (
    GeneratorNode,
    GroupNode,
    InstructionNode,
    LibraryNode,
    TreeNode,
)
from browser.tree.tree import Tree
from browser.utils import show_error_dialog, show_info_dialog
from configs.config import Config
from constants.browser import (
    EXT_FILE_LIBRARY,
    MSG_LIBRARY_GENERATION_CANCELLATION,
    MSG_LIBRARY_GENERATION_FAILED,
    MSG_LIBRARY_GENERATION_SUCCESS,
    NOD_LABEL_LIBRARIES,
    NOD_LABEL_NOT_LOADED,
    NOD_TYPE_GENERATOR,
    NOD_TYPE_GROUP,
    NOD_TYPE_INSTRUCTION,
    NOD_TYPE_LIBRARY,
    NOD_TYPE_LIBRARY_PLACEHOLDER,
    NOD_TYPE_ROOT,
    TITLE_DIALOG_LIBRARY_GENERATION_CANCELLED,
    TITLE_DIALOG_LIBRARY_GENERATION_SUCCESS,
)
from constants.enums import GeneratorClassName, LibraryGeneratorName
from constants.general import NOISE_PERIODS
from ffts.window import Window
from instructions.instruction import Instruction
from instructions.noise import NoiseInstruction
from instructions.pulse import PulseInstruction
from instructions.triangle import TriangleInstruction
from library.creator.creator import LibraryCreator
from library.data import LibraryData, LibraryFragment
from library.key import LibraryKey
from library.library import Library
from reconstructor.maps import LIBRARY_GENERATOR_CLASS_MAP
from utils.frequencies import pitch_to_name


class LibraryManager:
    def __init__(self, library_directory: Path) -> None:
        self.library = Library(directory=str(library_directory))
        self.library_files: Dict[LibraryKey, str] = {}
        self.current_library_key: Optional[LibraryKey] = None
        self.tree = Tree()
        self.creator: Optional[LibraryCreator] = None

    def set_library_directory(self, directory: Path) -> None:
        self.library = Library(directory=str(directory))
        self.gather_available_libraries()

    def gather_available_libraries(self) -> Dict[LibraryKey, str]:
        library_directory = Path(self.library.directory)
        if not library_directory.exists():
            self.library_files.clear()
            self.rebuild_tree()
            return {}

        new_library_files = {}
        for filepath in library_directory.iterdir():
            if filepath.is_file() and filepath.suffix == EXT_FILE_LIBRARY and self._is_library_file(filepath.stem):
                library_key = self._create_key_from_filename(filepath.stem)
                new_library_files[library_key] = filepath.stem

        removed_libraries = set(self.library_files.keys()) - set(new_library_files.keys())
        for removed_key in removed_libraries:
            if removed_key in self.library.data:
                del self.library.data[removed_key]

        self.library_files = new_library_files
        return self.library_files

    def get_available_libraries(self) -> Dict[LibraryKey, str]:
        return self.library_files.copy()

    def is_library_loaded(self, library_key: LibraryKey) -> bool:
        return library_key in self.library.data

    def load_library(self, library_key: LibraryKey) -> bool:
        if self.is_library_loaded(library_key):
            self.current_library_key = library_key
            return True

        if library_key not in self.library_files:
            return False

        self.library.load_data(library_key)
        self.current_library_key = library_key
        return True

    def get_path(self, library_key: LibraryKey) -> Path:
        return self.library.get_path(library_key)

    def get_library_data(self, library_key: LibraryKey) -> Optional[LibraryData]:
        return self.library.data.get(library_key)

    def get_library_instructions_by_generator(
        self, library_key: LibraryKey, generator_name: LibraryGeneratorName
    ) -> Dict[str, List[Tuple]]:
        library_data = self.get_library_data(library_key)
        if not library_data:
            return {}

        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        if not generator_class_name:
            return {}

        return self._parse_instructions_by_generator(library_data, generator_class_name)

    def get_all_generator_instructions(
        self, library_key: LibraryKey
    ) -> Dict[LibraryGeneratorName, Dict[str, List[Tuple]]]:
        result = {}
        for generator_name in LibraryGeneratorName:
            instructions = self.get_library_instructions_by_generator(library_key, generator_name)
            if instructions:
                result[generator_name] = instructions
        return result

    def sync_with_config_key(self, config_key: LibraryKey) -> Optional[LibraryKey]:
        if self.library_exists_for_key(config_key):
            self.current_library_key = config_key
            return config_key

        return None

    def library_exists_for_key(self, key: LibraryKey) -> bool:
        return self.library.exists(key)

    def generate_library(self, config: Config, window: Window, overwrite: bool = False) -> None:
        self.library.directory = config.general.library_directory

        self.creator = LibraryCreator(config)
        self.creator.set_callbacks(
            on_complete=self._on_generation_complete,
            on_error=self._on_generation_error,
            on_cancelled=self._on_generation_cancelled,
        )

        self.creator.start(window, overwrite)

    def _on_generation_complete(self, result: Tuple[LibraryKey, LibraryData]) -> None:
        key, library_data = result
        self.library.save_data(key, library_data)
        self.current_library_key = key
        show_info_dialog(MSG_LIBRARY_GENERATION_SUCCESS, TITLE_DIALOG_LIBRARY_GENERATION_SUCCESS)

    def _on_generation_error(self, exception: Exception) -> None:
        show_error_dialog(exception, MSG_LIBRARY_GENERATION_FAILED)

    def _on_generation_cancelled(self) -> None:
        show_info_dialog(MSG_LIBRARY_GENERATION_CANCELLATION, TITLE_DIALOG_LIBRARY_GENERATION_CANCELLED)

    def is_generating(self) -> bool:
        return self.creator is not None and self.creator.is_running()

    def cancel_generation(self) -> None:
        if self.creator:
            self.creator.cancel()

    def cleanup_creator(self) -> None:
        if self.creator:
            self.creator.cleanup()
            self.creator = None

    def clear_all_libraries(self) -> None:
        self.library.purge()
        self.library_files.clear()
        self.current_library_key = None

    def _is_library_file(self, filename: str) -> bool:
        file_parts = filename.split("_")
        if len(file_parts) != 10:
            return False
        if not file_parts[0] == "sr" or not file_parts[1].isdigit():
            return False
        if not file_parts[2] == "fl" or not file_parts[3].isdigit():
            return False
        if not file_parts[4] == "ws" or not file_parts[5].isdigit():
            return False
        if not file_parts[6] == "tg" or not file_parts[7].isdigit():
            return False
        if not file_parts[8] == "ch" or not all(c in "0123456789abcdef" for c in file_parts[9]):
            return False

        return True

    def _create_key_from_filename(self, filename: str) -> LibraryKey:
        file_parts = filename.split("_")
        if len(file_parts) != 10:
            raise ValueError(f"Invalid library file name format: {filename}")

        sample_rate = int(file_parts[1])
        frame_length = int(file_parts[3])
        window_size = int(file_parts[5])
        transformation_gamma = int(file_parts[7])
        config_hash = file_parts[9]

        return LibraryKey(
            sample_rate=sample_rate,
            frame_length=frame_length,
            window_size=window_size,
            transformation_gamma=transformation_gamma,
            config_hash=config_hash,
        )

    def _get_display_name_from_key(self, key: LibraryKey) -> str:
        sample_rate = key.sample_rate
        change_rate = round(sample_rate / key.frame_length)
        transformation_gamma = key.transformation_gamma
        hash_part = key.config_hash[:7]
        return f"{sample_rate}_{change_rate}_{transformation_gamma}_{hash_part}"

    def _get_display_name(self, filename: str) -> str:
        key = self._create_key_from_filename(filename)
        return self._get_display_name_from_key(key)

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

    def rebuild_tree(self) -> None:
        root = TreeNode(NOD_LABEL_LIBRARIES, node_type=NOD_TYPE_ROOT)

        for library_key in sorted(self.library_files.keys(), key=lambda k: self._get_display_name_from_key(k)):
            self._build_library_node(library_key, root)

        self.tree.set_root(root)

    def _build_library_node(self, library_key: LibraryKey, parent: TreeNode) -> LibraryNode:
        display_name = self._get_display_name_from_key(library_key)
        library_node = LibraryNode(display_name, node_type=NOD_TYPE_LIBRARY, library_key=library_key, parent=parent)

        if self.is_library_loaded(library_key):
            self._build_generator_nodes(library_key, library_node)
        else:
            self._create_placeholder_node(library_node)

        return library_node

    def _create_placeholder_node(self, parent: LibraryNode) -> LibraryNode:
        return LibraryNode(
            NOD_LABEL_NOT_LOADED, node_type=NOD_TYPE_LIBRARY_PLACEHOLDER, library_key=parent.library_key, parent=parent
        )

    def _build_generator_nodes(self, library_key: LibraryKey, parent: TreeNode) -> None:
        for generator_name in LibraryGeneratorName:
            grouped_instructions = self.get_library_instructions_by_generator(library_key, generator_name)

            if not grouped_instructions:
                continue

            generator_node = GeneratorNode(
                generator_name.value.capitalize(),
                node_type=NOD_TYPE_GENERATOR,
                generator_name=generator_name,
                parent=parent,
            )

            self._build_group_nodes(generator_name, grouped_instructions, generator_node)

    def _build_group_nodes(
        self,
        generator_name: LibraryGeneratorName,
        grouped_instructions: Dict[str, List[Tuple]],
        parent: TreeNode,
    ) -> None:
        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        if not generator_class_name:
            raise ValueError(f"No generator class name found for {generator_name}")

        for group_key, instructions in grouped_instructions.items():
            group_label = f"{group_key} ({len(instructions)} item(s))"
            group_node = GroupNode(
                group_label,
                node_type=NOD_TYPE_GROUP,
                generator_name=generator_name,
                group_key=group_key,
                parent=parent,
            )

            for instruction, fragment in instructions:
                InstructionNode(
                    instruction.name,
                    node_type=NOD_TYPE_INSTRUCTION,
                    generator_name=generator_name,
                    generator_class_name=generator_class_name,
                    instruction=instruction,
                    fragment=fragment,
                    parent=group_node,
                )

    def refresh_library_node(self, library_key: LibraryKey) -> None:
        if not self.tree.root:
            return

        library_node = self.tree.find_node(
            lambda node: isinstance(node, LibraryNode)
            and node.node_type == NOD_TYPE_LIBRARY
            and node.library_key == library_key
        )

        if library_node and isinstance(library_node, LibraryNode):
            for child in list(library_node.children):
                child.parent = None

            if self.is_library_loaded(library_key):
                self._build_generator_nodes(library_key, library_node)
            else:
                self._create_placeholder_node(library_node)
