from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sampletones.configs import Config
from sampletones.constants.enums import GeneratorClassName, LibraryGeneratorName
from sampletones.constants.paths import EXT_FILE_LIBRARY
from sampletones.ffts import Window
from sampletones.generators import LIBRARY_GENERATOR_CLASS_MAP
from sampletones.instructions import (
    Instruction,
    NoiseInstruction,
    PulseInstruction,
    TriangleInstruction,
)
from sampletones.instructions.typehints import InstructionUnion
from sampletones.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
    InstructionLibraryKey,
)
from sampletones.library.creator import InstructionsLibraryCreator
from sampletones.parallelization import TaskProgress, TaskStatus
from sampletones.tree import GeneratorNode, LibraryNode, NodeType, Tree, TreeNode
from sampletones.typehints import VoidCallback
from sampletones.utils import period_to_name, pitch_to_name, to_path
from sampletones.utils.callbacks import CallbackMixin

from ..config.manager import ConfigManager
from ..constants.instructions import (
    LBL_NODE_INSTRUCTIONS_LIBRARY_LIBRARIES,
    LBL_NODE_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
)
from ..instruction.data import InstructionPanelData

InstructionsList = List[Tuple[Instruction, InstructionLibraryFragment[Any]]]

OnGenerationProgressCallback = Callable[[TaskStatus, TaskProgress], None]
OnGenerationErrorCallback = Callable[[Exception], None]


class InstructionsLibraryManager(CallbackMixin):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        library_directory = config_manager.get_library_directory()
        self.library = InstructionLibrary(directory=str(library_directory))
        self.library_files: Dict[InstructionLibraryKey, str] = {}
        self.current_library_key: Optional[InstructionLibraryKey] = None
        self.current_instruction: Optional[InstructionPanelData] = None

        self.tree = Tree()
        self.creator: Optional[InstructionsLibraryCreator] = None

        self.on_generation_start: Optional[VoidCallback] = None
        self.on_generation_completed: Optional[VoidCallback] = None
        self.on_generation_progress: Optional[OnGenerationProgressCallback] = None
        self.on_generation_error: Optional[OnGenerationErrorCallback] = None
        self.on_generation_cancelled: Optional[VoidCallback] = None

    def set_library_directory(self, directory: Path) -> None:
        self.library = InstructionLibrary(directory=str(directory))
        self.gather_available_libraries()

    def gather_available_libraries(self) -> Dict[InstructionLibraryKey, str]:
        library_directory = to_path(self.library.directory)
        if not library_directory.exists():
            self.library_files.clear()
            self.rebuild_tree()
            return {}

        new_library_files = {}
        for filepath in library_directory.iterdir():
            if filepath.is_file() and filepath.suffix == EXT_FILE_LIBRARY and self._is_library_file(filepath.stem):
                library_key = self.create_key_from_filename(filepath.stem)
                new_library_files[library_key] = filepath.stem

        removed_libraries = set(self.library_files.keys()) - set(new_library_files.keys())
        for removed_key in removed_libraries:
            if removed_key in self.library.data:
                del self.library.data[removed_key]

        self.library_files = new_library_files
        return self.library_files

    def get_available_libraries(self) -> Dict[InstructionLibraryKey, str]:
        return self.library_files.copy()

    def is_library_loaded(self, library_key: Optional[InstructionLibraryKey] = None) -> bool:
        if library_key is None:
            if self.current_library_key is None:
                return False

            library_key = self.current_library_key

        filepath = self.get_path(library_key)
        if not filepath.exists():
            return False

        return library_key in self.library.data

    def load_library(self, library_key: InstructionLibraryKey) -> bool:
        if self.is_library_loaded(library_key):
            self.current_library_key = library_key
            return True

        if library_key not in self.library_files:
            return False

        self.library.load_data(library_key)
        self.current_library_key = library_key
        return True

    def load_library_file(self, filepath: Path) -> InstructionLibraryKey:
        library_key = self.create_key_from_filename(filepath.stem)
        self.library.load_data(library_key)
        self.current_library_key = library_key
        return library_key

    def load_instruction(self, instruction: InstructionUnion) -> Optional[InstructionPanelData]:
        if not self.current_library_key or not self.is_library_loaded(self.current_library_key):
            return None

        data = self.library.data[self.current_library_key]
        fragment = data[instruction]
        library_config = data.config
        self.current_instruction = InstructionPanelData(
            instruction=instruction,
            config=library_config,
            fragment=fragment,
        )

        return self.current_instruction

    def get_current_instruction(self) -> Optional[InstructionPanelData]:
        return self.current_instruction

    def get_path(self, library_key: InstructionLibraryKey) -> Path:
        return self.library.get_path(library_key)

    def get_library_data(self, library_key: InstructionLibraryKey) -> Optional[InstructionLibraryData]:
        return self.library.data.get(library_key)

    def get_library_instructions_by_generator(
        self, library_key: InstructionLibraryKey, generator_name: LibraryGeneratorName
    ) -> Dict[str, InstructionsList]:
        library_data = self.get_library_data(library_key)
        if not library_data:
            return {}

        generator_class_name = LIBRARY_GENERATOR_CLASS_MAP.get(generator_name)
        if not generator_class_name:
            return {}

        return self._parse_instructions_by_generator(library_data, generator_class_name)

    def get_all_generator_instructions(
        self,
        library_key: InstructionLibraryKey,
    ) -> Dict[LibraryGeneratorName, Dict[str, InstructionsList]]:
        result = {}
        for generator_name in LibraryGeneratorName:
            instructions = self.get_library_instructions_by_generator(library_key, generator_name)
            if instructions:
                result[generator_name] = instructions
        return result

    def sync_with_config_key(self, config_key: InstructionLibraryKey) -> Optional[InstructionLibraryKey]:
        if self.library_exists_for_key(config_key):
            self.current_library_key = config_key
            return config_key

        return None

    def library_exists_for_key(self, key: InstructionLibraryKey) -> bool:
        return self.library.exists(key)

    def generate_library(self, config: Config, window: Window) -> None:
        self.library = InstructionLibrary.from_config(config)
        self.creator = InstructionsLibraryCreator(config, window)
        self.creator.set_callbacks(
            on_start=self.on_generation_start,
            on_completed=self._complete_generation,
            on_error=self.on_generation_error,
            on_cancelled=self.on_generation_cancelled,
            on_progress=self.on_generation_progress,
        )

        self.creator.start()

    def _complete_generation(self, result: Tuple[InstructionLibraryKey, InstructionLibraryData]) -> None:
        try:
            key, library_data = result
            self.library.save_data(key, library_data)
            self.current_library_key = key
        except Exception as exception:
            self.call(self.on_generation_error, exception)
            raise exception

        self.call(self.on_generation_completed)

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
        if not file_parts[2] == "cr" or not file_parts[3].isdigit():
            return False
        if not file_parts[4] == "ws" or not file_parts[5].isdigit():
            return False
        if not file_parts[6] == "tg" or not file_parts[7].isdigit():
            return False
        if not file_parts[8] == "ch" or not all(c in "0123456789abcdef" for c in file_parts[9]):
            return False

        return True

    # TODO: change; relying on the filename is error-prone
    def create_key_from_filename(self, filename: str) -> InstructionLibraryKey:
        file_parts = filename.split("_")
        if len(file_parts) != 10:
            raise ValueError(f"Invalid library file name format: {filename}")

        sample_rate = int(file_parts[1])
        change_rate = int(file_parts[3])
        window_size = int(file_parts[5])
        transformation_gamma = int(file_parts[7])
        config_hash = file_parts[9]
        frame_length = round(sample_rate / change_rate)

        return InstructionLibraryKey(
            sample_rate=sample_rate,
            frame_length=frame_length,
            window_size=window_size,
            transformation_gamma=transformation_gamma,
            config_hash=config_hash,
            filename=f"{filename}{EXT_FILE_LIBRARY}",
        )

    def get_display_name_from_key(self, key: InstructionLibraryKey) -> str:
        sample_rate = key.sample_rate
        change_rate = round(sample_rate / key.frame_length)
        transformation_gamma = key.transformation_gamma
        hash_part = key.config_hash[:7]
        return f"{sample_rate}_{change_rate}_{transformation_gamma}_{hash_part}"

    def _get_display_name(self, filename: str) -> str:
        key = self.create_key_from_filename(filename)
        return self.get_display_name_from_key(key)

    def _parse_instructions_by_generator(
        self,
        library_data: InstructionLibraryData,
        generator_class_name: GeneratorClassName,
    ) -> Dict[str, InstructionsList]:
        generator_data = library_data.filter(generator_class_name)
        if not generator_data:
            return {}

        instructions: Dict[str, InstructionsList] = {}
        sorted_generator_data = dict(sorted(generator_data.items(), key=lambda item: item[0]))
        for instruction, fragment in sorted_generator_data.items():
            if not instruction.on:
                continue

            if isinstance(instruction, (PulseInstruction, TriangleInstruction)):
                grouping_key = pitch_to_name(instruction.pitch)
            elif isinstance(instruction, NoiseInstruction):
                grouping_key = period_to_name(instruction.period)
            else:
                raise TypeError(f"Unsupported instruction type {type(instruction)} for grouping")

            if grouping_key not in instructions:
                instructions[grouping_key] = []

            instructions[grouping_key].append((instruction, fragment))

        return instructions

    def rebuild_tree(self) -> None:
        root = TreeNode(LBL_NODE_INSTRUCTIONS_LIBRARY_LIBRARIES, node_type=NodeType.ROOT)

        for library_key in sorted(self.library_files.keys(), key=self.get_display_name_from_key):
            self._build_library_node(library_key, root)

        self.tree.set_root(root)

    def _build_library_node(self, library_key: InstructionLibraryKey, parent: TreeNode) -> LibraryNode:
        display_name = self.get_display_name_from_key(library_key)
        library_node = LibraryNode(display_name, library_key=library_key, parent=parent)

        if self.is_library_loaded(library_key):
            self._build_generator_nodes(library_key, library_node)
        else:
            self._create_placeholder_node(library_node)

        return library_node

    def _create_placeholder_node(self, parent: LibraryNode) -> LibraryNode:
        return LibraryNode(
            LBL_NODE_INSTRUCTIONS_LIBRARY_LOAD_LIBRARY,
            node_type=NodeType.PLACEHOLDER,
            library_key=parent.library_key,
            parent=parent,
        )

    def _build_generator_nodes(self, library_key: InstructionLibraryKey, parent: TreeNode) -> None:
        for generator_name in LibraryGeneratorName:
            grouped_instructions = self.get_library_instructions_by_generator(library_key, generator_name)

            if not grouped_instructions:
                continue

            GeneratorNode(
                generator_name.value.capitalize(),
                generator_name=generator_name,
                parent=parent,
            )

    def refresh_library_node(self, library_key: InstructionLibraryKey) -> None:
        if not self.tree.root:
            return

        library_node = self.tree.find_node(
            lambda node: isinstance(node, LibraryNode) and node.library_key == library_key
        )

        if library_node and isinstance(library_node, LibraryNode):
            for child in list(library_node.children):
                child.parent = None

            if self.is_library_loaded(library_key):
                self._build_generator_nodes(library_key, library_node)
            else:
                self._create_placeholder_node(library_node)
