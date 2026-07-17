from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sampletones_application.categories.elements.instructions import (
    InstructionsLibraryElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_core.configs import Config
from sampletones_core.constants.enums import LibraryGeneratorName
from sampletones_core.fft import Window
from sampletones_core.instructions import Instruction
from sampletones_core.instructions.types import InstructionUnion
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryFragment,
    InstructionLibraryKey,
    create_key_from_filename,
    get_display_name_from_key,
)
from sampletones_core.library.creator import InstructionsLibraryCreator
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.parallelization import TaskProgress, TaskStatus
from sampletones_core.paths import EXT_FILE_LIBRARY
from sampletones_core.structures.tree import (
    GeneratorNode,
    LibraryNode,
    NodeType,
    Tree,
    TreeNode,
)
from sampletones_shared.logger import logger
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import to_path

InstructionsList = List[Tuple[Instruction, InstructionLibraryFragment[Any]]]

OnGenerationProgressCallback = Callable[[TaskStatus, TaskProgress], None]
OnGenerationErrorCallback = Callable[[Exception], None]


class InstructionsLibraryManager(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._config_manager = config_manager
        self._libraries_node_label = language_manager[
            Page.INSTRUCTIONS,
            Panel.LIBRARY,
            TextType.LABEL,
            InstructionsLibraryElements.LIBRARIES_NODE,
        ]
        library_directory = config_manager.get_library_directory()
        self._library = InstructionLibrary(directory=str(library_directory))
        self._library_files: Dict[InstructionLibraryKey, str] = {}
        self._current_library_key: Optional[InstructionLibraryKey] = None

        self._tree = Tree()
        self._creator: Optional[InstructionsLibraryCreator] = None

        self.on_generation_start: Optional[VoidCallback] = None
        self.on_generation_completed: Optional[VoidCallback] = None
        self.on_generation_progress: Optional[OnGenerationProgressCallback] = None
        self.on_generation_progress_extra: Optional[OnGenerationProgressCallback] = None
        self.on_generation_error: Optional[OnGenerationErrorCallback] = None
        self.on_generation_cancelled: Optional[VoidCallback] = None

    def set_library_directory(self, directory: Path) -> None:
        self._library = InstructionLibrary(directory=str(directory))
        self.gather_available_libraries()

    def gather_available_libraries(self) -> Dict[InstructionLibraryKey, str]:
        library_directory = to_path(self._library.directory)
        if not library_directory.exists():
            self._library_files.clear()
            self.rebuild_tree()
            return {}

        new_library_files = {}
        for filepath in library_directory.iterdir():
            if filepath.is_file() and filepath.suffix == EXT_FILE_LIBRARY and self._is_library_file(filepath.stem):
                library_key = create_key_from_filename(filepath)
                new_library_files[library_key] = filepath.stem

        removed_libraries = set(self._library_files.keys()) - set(new_library_files.keys())
        for removed_key in removed_libraries:
            if removed_key in self._library.data:
                del self._library.data[removed_key]

        self._library_files = new_library_files
        return self._library_files

    def get_available_libraries(self) -> Dict[InstructionLibraryKey, str]:
        return self._library_files.copy()

    def get_library_key(self, library_key: Optional[InstructionLibraryKey] = None) -> Optional[InstructionLibraryKey]:
        if library_key is None:
            if self._current_library_key is None:
                return None

            library_key = self._current_library_key

        return library_key

    def is_library_loaded(self, library_key: Optional[InstructionLibraryKey] = None) -> bool:
        library_key = self.get_library_key(library_key)
        if not self.does_library_exist(library_key):
            return False

        return library_key in self._library.data

    def does_library_exist(self, library_key: Optional[InstructionLibraryKey] = None) -> bool:
        library_key = self.get_library_key(library_key)
        if library_key is None:
            return False

        filepath = self.get_path(library_key)
        return filepath.exists()

    def load_library(self, library_key: InstructionLibraryKey) -> bool:
        if self.is_library_loaded(library_key):
            self._current_library_key = library_key
            return True

        if library_key not in self._library_files:
            return False

        self._library.load_data(library_key)
        self._current_library_key = library_key
        return True

    def load_library_file(self, path: Path) -> InstructionLibraryKey:
        logger.info(f"Loading library data: {logger.format_path(path)}")
        library_key = create_key_from_filename(path)
        self._library.load_data(library_key)
        self._current_library_key = library_key
        logger.info(f"Library data: {logger.format_path(path)} loaded successfully")
        return library_key

    def load_instruction(self, instruction: InstructionUnion) -> Optional[InstructionPanelData]:
        if not self._current_library_key or not self.is_library_loaded(self._current_library_key):
            return None

        data = self._library.data[self._current_library_key]
        fragment = data[instruction]
        library_config = data.config
        instruction_data = InstructionPanelData(
            library_key=self._current_library_key,
            instruction=instruction,
            config=library_config,
            fragment=fragment,
        )

        return instruction_data

    def get_path(self, library_key: InstructionLibraryKey) -> Path:
        return self._library.get_path(library_key)

    def get_library_data(self, library_key: InstructionLibraryKey) -> Optional[InstructionLibraryData]:
        return self._library.data.get(library_key)

    def sync_with_config_key(self, config_key: InstructionLibraryKey) -> Optional[InstructionLibraryKey]:
        if self.library_exists_for_key(config_key):
            self._current_library_key = config_key
            return config_key

        return None

    def library_exists_for_key(self, key: InstructionLibraryKey) -> bool:
        return self._library.exists(key)

    def is_library_available_for_config(self) -> bool:
        return self.library_exists_for_key(self._config_manager.key)

    def generate_library(self, config: Config, window: Window) -> None:
        self._creator = InstructionsLibraryCreator(config, window)

        _primary = self.on_generation_progress
        _extra = self.on_generation_progress_extra

        def _on_progress(status: TaskStatus, progress: TaskProgress) -> None:
            if _primary:
                _primary(status, progress)
            if _extra:
                _extra(status, progress)

        self._creator.set_callbacks(
            on_start=self.on_generation_start,
            on_completed=self._complete_generation,
            on_error=self.on_generation_error,
            on_cancelled=self.on_generation_cancelled,
            on_progress=_on_progress,
        )

        self._creator.start()

    def _complete_generation(self, result: Tuple[InstructionLibraryKey, InstructionLibraryData]) -> None:
        key, library_data = result
        try:
            self._library.save_data(key, library_data)
            self._current_library_key = key
        except OSError as exception:
            self.call(self.on_generation_error, exception)
            raise

        self.call(self.on_generation_completed)

    def is_generating(self) -> bool:
        """A generation is in progress from the moment a creator is started until it is cleaned up.

        Creator presence is the source of truth: it spans the saving and finalising step that runs
        after the worker thread clears its own ``is_running`` flag, so the generation reads as in
        progress right up to cleanup.
        """
        return self._creator is not None

    @property
    def tree(self) -> Tree:
        return self._tree

    @property
    def current_library_key(self) -> Optional[InstructionLibraryKey]:
        return self._current_library_key

    def clear_current_library(self) -> None:
        self._current_library_key = None

    @property
    def creator(self) -> Optional[InstructionsLibraryCreator]:
        return self._creator

    def cancel_generation(self) -> None:
        if self._creator:
            self._creator.cancel()

    def cleanup_creator(self) -> None:
        if self._creator:
            self._creator.cleanup()
            self._creator = None

    def shutdown(self) -> None:
        """Tears the library creator's process pool down synchronously for application exit.

        A conversion generates its library first, so this pool is the one still spawning
        workers when a run is cancelled and the window is closed; this blocks until it has
        stopped so the process reaps its workers before releasing shared resources."""
        if self._creator:
            self._creator.shutdown()
            self._creator = None

    def clear_all_libraries(self) -> None:
        self._library.purge()
        self._library_files.clear()
        self._current_library_key = None

    def _is_library_file(self, filename: str) -> bool:
        """Whether ``filename`` parses as a library filename, per the field schema that builds it.

        Delegates to :class:`InstructionsFilenameFields`, the single source of truth for the
        ``sr_…_nf_…_ws_…_tg_…_ch_…`` layout: a malformed or out-of-range name raises (``ValueError``,
        which pydantic's ``ValidationError`` subclasses) and is reported as not-a-library-file.
        """
        try:
            InstructionsFilenameFields.create(filename)
        except ValueError:
            return False

        return True

    def _get_display_name(self, filename: str) -> str:
        key = create_key_from_filename(filename)
        return get_display_name_from_key(key)

    def rebuild_tree(self) -> None:
        root = TreeNode(self._libraries_node_label, node_type=NodeType.ROOT)

        for library_key in sorted(self._library_files.keys(), key=get_display_name_from_key):
            self._build_library_node(library_key, root)

        self._tree.set_root(root)

    def _build_library_node(self, library_key: InstructionLibraryKey, parent: TreeNode) -> LibraryNode:
        display_name = get_display_name_from_key(library_key)
        library_node = LibraryNode(display_name, library_key=library_key, parent=parent)
        self._build_generator_nodes(library_node)
        return library_node

    def _build_generator_nodes(self, parent: TreeNode) -> None:
        for generator_name in LibraryGeneratorName:
            GeneratorNode(
                generator_name.value.capitalize(),
                generator_name=generator_name,
                parent=parent,
            )

    def refresh_library_node(self, library_key: InstructionLibraryKey) -> None:
        if not self._tree.root:
            return

        library_node = self._tree.find_node(
            lambda node: isinstance(node, LibraryNode) and node.library_key == library_key
        )

        if library_node and isinstance(library_node, LibraryNode):
            for child in list(library_node.children):
                child.parent = None

            self._build_generator_nodes(library_node)
