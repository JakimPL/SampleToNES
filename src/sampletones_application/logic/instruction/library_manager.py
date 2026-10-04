import threading
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.config.managers.config import ConfigManager
from sampletones_application.logic.instruction.readiness import LibraryReadiness
from sampletones_application.view_model.instruction.data import InstructionPanelData
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.fft import Window
from sampletones_core.instructions.types import InstructionUnion
from sampletones_core.library import (
    InstructionLibrary,
    InstructionLibraryData,
    InstructionLibraryKey,
    LibraryHeader,
    LibraryState,
    create_key_from_filename,
    get_display_name_from_key,
    library_state,
)
from sampletones_core.library.creator import InstructionsLibraryCreator
from sampletones_core.library.filename.fields import InstructionsFilenameFields
from sampletones_core.parallelization import TaskProgress, TaskStatus
from sampletones_core.structures.tree import (
    GeneratorNode,
    LibraryNode,
    NodeType,
    Tree,
    TreeNode,
)
from sampletones_shared.paths.extensions import EXT_FILE_LIBRARY
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin
from sampletones_shared.utils.system.paths import to_path

OnGenerationProgressCallback = Callable[[TaskStatus, TaskProgress], None]
OnGenerationErrorCallback = Callable[[Exception], None]


@dataclass
class _Catalog:
    """The libraries one directory holds in memory, and the one taken up as current there.

    Only the directory the catalog stands at holds libraries in memory. Every directory keeps its
    choice of current library. A directory left keeps, as ``released_key``, the current library it
    had loaded, which the reader coming back gets loaded again.
    """

    library: InstructionLibrary
    current_key: Optional[InstructionLibraryKey]
    released_key: Optional[InstructionLibraryKey] = None

    def name_by(self, directory: Path) -> None:
        """Names the folder by ``directory``, the spelling the reader configured last, keeping what the
        folder holds.

        Every spelling names one folder, so a generation writing through the spelling it read first
        lands in the same place.
        """
        spelling = str(directory)
        if self.library.directory != spelling:
            self.library = self.library.model_copy(update={"directory": spelling})

    def release(self) -> None:
        """Lets go of every library loaded here, remembering the current one where it was loaded.

        A release still waiting to be taken stays until a loaded current library replaces it.
        """
        if self.current_key is not None and self.current_key in self.library.data:
            self.released_key = self.current_key

        self.library.data.clear()


class InstructionsLibraryManager(CallbackMixin):
    def __init__(
        self,
        config_manager: ConfigManager,
        *,
        language_manager: LanguageManager,
    ) -> None:
        self._language_manager = language_manager
        self._config_manager = config_manager
        self._catalogs: Dict[Path, _Catalog] = {}
        self._catalog_lock = threading.Lock()
        self._catalog = self._catalog_at(config_manager.get_library_directory())
        self._listed_libraries: Dict[InstructionLibraryKey, bool] = {}

        self._tree = Tree()
        self._creator: Optional[InstructionsLibraryCreator] = None

        self.on_generation_start: Optional[VoidCallback] = None
        self.on_generation_completed: Optional[VoidCallback] = None
        self.on_generation_progress: Optional[OnGenerationProgressCallback] = None
        self.on_generation_progress_extra: Optional[OnGenerationProgressCallback] = None
        self.on_generation_error: Optional[OnGenerationErrorCallback] = None
        self.on_generation_canceled: Optional[VoidCallback] = None

    @property
    def library_directory(self) -> Path:
        return to_path(self._catalog.library.directory)

    def set_library_directory(self, directory: Path) -> bool:
        """Roots the catalog at ``directory``, and answers whether that moved it to another folder.

        The folder left lets go of the libraries it loaded and keeps the one it had taken up as
        current. Where that library was loaded, the folder remembers it, and a reader coming back
        gets it from :meth:`take_released_library` to load again. Every spelling of one folder, a
        link to it included, names the same catalog, and the catalog goes by the spelling given last.
        """
        catalog = self._catalog_at(directory)
        with self._catalog_lock:
            catalog.name_by(to_path(directory))
            if catalog is self._catalog:
                return False

            self._catalog.release()
            self._catalog = catalog

        return True

    def take_released_library(self) -> Optional[InstructionLibraryKey]:
        """The library the folder the catalog stands at had loaded when the reader last left it, handed
        over once."""
        with self._catalog_lock:
            key = self._catalog.released_key
            self._catalog.released_key = None

        return key

    def _catalog_at(self, directory: Path) -> _Catalog:
        """The catalog of the folder ``directory`` names, started empty under that spelling the first time
        the folder is read."""
        spelling = to_path(directory)
        root = spelling.resolve()
        catalog = self._catalogs.get(root)
        if catalog is None:
            catalog = _Catalog(
                library=InstructionLibrary(directory=str(spelling)),
                current_key=None,
            )
            self._catalogs[root] = catalog

        return catalog

    def gather_available_libraries(self) -> None:
        """Lists the library files standing in the catalog's directory, marking each one another
        version built, and lets go of the libraries whose files are gone."""
        library_directory = self.library_directory
        listed: Dict[InstructionLibraryKey, bool] = {}
        if library_directory.exists():
            for filepath in library_directory.iterdir():
                if filepath.is_file() and filepath.suffix == EXT_FILE_LIBRARY and self._is_library_file(filepath.stem):
                    listed[create_key_from_filename(filepath)] = library_state(filepath) is LibraryState.OUTDATED

        loaded = self._catalog.library.data
        for removed_key in set(loaded) - set(listed):
            del loaded[removed_key]

        self._listed_libraries = listed

    def is_library_loaded(self, library_key: InstructionLibraryKey) -> bool:
        """Whether the catalog holds the library ``library_key`` names in memory.

        A load takes only a library this build reads, so a library held here is one to use as it
        stands.
        """
        return library_key in self._catalog.library.data

    def library_state(self, library_key: InstructionLibraryKey) -> LibraryState:
        """Where the library ``library_key`` names stands in the catalog for this build."""
        return self._catalog.library.state(library_key)

    def stored_config(self, library_key: InstructionLibraryKey) -> Optional[InstructionsLibraryConfig]:
        """The settings the library ``library_key`` names states it was built for, where its file
        states them in a form this build reads."""
        try:
            return LibraryHeader.read(self.get_path(library_key)).config
        except FileNotFoundError:
            return None

    def load_library(self, library_key: InstructionLibraryKey) -> InstructionLibraryData:
        """Takes up the library ``library_key`` names as the current one, reading it from its file
        where the catalog holds it in no memory yet."""
        if not self.is_library_loaded(library_key):
            self._catalog.library.load_data(library_key)

        self._catalog.current_key = library_key
        return self._catalog.library.data[library_key]

    def load_instruction(
        self,
        instruction: InstructionUnion,
    ) -> Optional[InstructionPanelData]:
        current_key = self._catalog.current_key
        if not current_key or not self.is_library_loaded(current_key):
            return None

        data = self._catalog.library.data[current_key]
        fragment = data[instruction]
        library_config = data.config
        instruction_data = InstructionPanelData(
            library_key=current_key,
            instruction=instruction,
            config=library_config,
            fragment=fragment,
        )

        return instruction_data

    def get_path(self, library_key: InstructionLibraryKey) -> Path:
        return self._catalog.library.get_path(library_key)

    def sync_with_config_key(
        self,
        config_key: InstructionLibraryKey,
    ) -> Optional[InstructionLibraryKey]:
        if self.library_state(config_key) is LibraryState.CURRENT:
            self._catalog.current_key = config_key
            return config_key

        return None

    def library_readiness(
        self,
        directory: Path,
        key: InstructionLibraryKey,
    ) -> LibraryReadiness:
        """Where the library ``key`` names under ``directory`` stands for a conversion waiting on it.

        A generation writes its file while it runs, so the file counts only once the generation has
        been released. A library this build reads is then ready, and any other is one the conversion
        will not get.
        """
        if self.is_generating():
            return LibraryReadiness.PREPARING

        if library_state(directory / key.filename) is LibraryState.CURRENT:
            return LibraryReadiness.READY

        return LibraryReadiness.MISSING

    def generate_library(self, config: Config, window: Window) -> None:
        """Starts a generation that writes into the catalog standing at the moment it is asked for.

        The library directory may move while the generation runs; the library still lands where the
        generation was started, which is where the configuration it was started from points.
        """
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
            on_completed=partial(self._complete_generation, self._catalog),
            on_error=self.on_generation_error,
            on_canceled=self.on_generation_canceled,
            on_progress=_on_progress,
        )

        self._creator.start()

    def _complete_generation(
        self,
        catalog: _Catalog,
        result: Tuple[InstructionLibraryKey, InstructionLibraryData],
    ) -> None:
        """Writes the generated library into ``catalog``, the one the generation was started in, and
        makes it that catalog's current library.

        The library stays in memory only where the catalog still stands there. A catalog left holds
        the file and the choice, and remembers the library as loaded, so the reader coming back
        loads it from the file.
        """
        key, library_data = result
        try:
            catalog.library.write_data(key, library_data)
        except OSError as exception:
            self.call(self.on_generation_error, exception)
            raise

        with self._catalog_lock:
            catalog.current_key = key
            if catalog is self._catalog:
                catalog.library.data[key] = library_data
            else:
                catalog.released_key = key

        self.call(self.on_generation_completed)

    def is_generating(self) -> bool:
        """A generation is in progress from the moment a creator is started until it is released.

        Creator presence is the source of truth: it spans the saving step that runs after the
        workers have ended and the release that follows the announcement, so the generation reads
        as in progress right up to the moment nothing of it is left running.
        """
        return self._creator is not None

    @property
    def tree(self) -> Tree:
        return self._tree

    @property
    def current_library_key(self) -> Optional[InstructionLibraryKey]:
        """The library taken up as current in the catalog standing now."""
        return self._catalog.current_key

    def clear_current_library(self) -> None:
        self._catalog.current_key = None

    @property
    def creator(self) -> Optional[InstructionsLibraryCreator]:
        return self._creator

    def cancel_generation(self) -> None:
        if self._creator:
            self._creator.cancel()

    def release_creator(self) -> None:
        """Ends the creator's run and lets the creator go once its pool has ended.

        The generation reads as in progress until then, so nothing that waits on it — a conversion
        preparing its library, a new generation, the application's exit — meets a worker still
        alive. A creator that has announced its outcome has already ended its pool, so this returns
        at once; at exit it cancels a generation still under way and waits for its workers.
        """
        if self._creator is not None:
            self._creator.shutdown()
            self._creator = None

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

    def rebuild_tree(self) -> None:
        root = TreeNode(self._language_manager["instructions.library.label.libraries_node"], node_type=NodeType.ROOT)

        for library_key in sorted(self._listed_libraries, key=get_display_name_from_key):
            self._build_library_node(library_key, root)

        self._tree.set_root(root)

    def _build_library_node(
        self,
        library_key: InstructionLibraryKey,
        parent: TreeNode,
    ) -> LibraryNode:
        display_name = get_display_name_from_key(library_key)
        library_node = LibraryNode(
            display_name,
            library_key=library_key,
            outdated=self._listed_libraries[library_key],
            parent=parent,
        )
        if not library_node.outdated:
            self._build_generator_nodes(library_node)
        return library_node

    def _build_generator_nodes(self, parent: TreeNode) -> None:
        for generator_name in GeneratorName:
            GeneratorNode(
                generator_name.value.capitalize(),
                generator_name=generator_name,
                parent=parent,
            )
