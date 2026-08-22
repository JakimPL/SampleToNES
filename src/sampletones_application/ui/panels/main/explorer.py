from pathlib import Path
from typing import Any, Callable, List, Optional, Protocol, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.main import (
    TAG_MAIN_EXPLORER_BUTTON_REFRESH,
    TAG_MAIN_EXPLORER_GROUP_CONTROLS,
    TAG_MAIN_EXPLORER_GROUP_TREE,
    TAG_MAIN_EXPLORER_PANEL,
    TAG_MAIN_EXPLORER_TREE,
    TAG_MAIN_EXPLORER_WINDOW_TREE,
)
from sampletones_application.ui.elements.context_menu import context_menu
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.browser import GUIFileBrowserPanel
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.elements.tree.tree import NO_EXPANDED_ROWS
from sampletones_application.utils.gui.keyboard.modifiers import Modifier, capture_modifiers
from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    TreeTraversal,
    traverse,
)
from sampletones_shared.paths import extensions
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import MessageCallback, PathCallback


class ExplorerLogicProtocol(Protocol):
    """The filesystem-exploration contract ``GUIExplorerPanel`` drives.

    Typing the collaborator structurally keeps the panel bound to the exact
    query surface its tree rendering needs — per-directory expansion and
    content checks run synchronously during node construction — while the
    owning coordinator constructs the real logic object and injects it.
    """

    @property
    def tree(self) -> Tree: ...

    def refresh_tree(self) -> None: ...

    def collapse_all(self) -> None: ...

    def expand_directory(self, node: FileSystemNode) -> None: ...

    def has_loaded_children(self, filepath: Path) -> bool: ...

    def is_directory_open(self, filepath: Path) -> bool: ...

    def set_directory_open(self, filepath: Path, is_open: bool) -> None: ...

    def has_relevant_content(self, filepath: Path) -> bool: ...


class GUIExplorerPanel(GUIFileBrowserPanel):
    """The Main tab's browser of the filesystem, whose rows are the folders and files on disk."""

    _tags: FileBrowserTags = FileBrowserTags(
        panel=TAG_MAIN_EXPLORER_PANEL,
        tree=TAG_MAIN_EXPLORER_TREE,
        window_tree=TAG_MAIN_EXPLORER_WINDOW_TREE,
        group_tree=TAG_MAIN_EXPLORER_GROUP_TREE,
        group_controls=TAG_MAIN_EXPLORER_GROUP_CONTROLS,
        button_refresh=TAG_MAIN_EXPLORER_BUTTON_REFRESH,
    )

    def __init__(
        self,
        explorer_logic: ExplorerLogicProtocol,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
    ) -> None:
        self._language_manager = language_manager
        self._explorer_logic = explorer_logic

        self.on_wave_file_clicked: Optional[PathCallback] = None
        self.on_directory_clicked: Optional[PathCallback] = None
        self.on_directory_add_requested: Optional[PathCallback] = None
        self.on_file_add_requested: Optional[PathCallback] = None
        self.can_add_stems: Optional[Callable[[], bool]] = None
        self.on_reconstruct_directory: Optional[PathCallback] = None
        self.on_reconstruct_file: Optional[PathCallback] = None
        self.on_load_reconstruction: Optional[PathCallback] = None
        self.on_load_library: Optional[PathCallback] = None
        self.on_set_as_reconstructions_directory: Optional[PathCallback] = None
        self.on_set_as_library_directory: Optional[PathCallback] = None

        super().__init__(
            tree=explorer_logic.tree,
            tree_logic=tree_logic,
            scheduling=scheduling,
            search_label=language_manager["global.browser.label.filter"],
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
            initial_collapsed=initial_collapsed,
            initial_favorites_only=False,
            initial_expanded_rows=NO_EXPANDED_ROWS,
        )

    @property
    def section_label(self) -> str:
        return self._language_manager["main.explorer.label.section"]

    @property
    def section_glyph(self) -> str:
        return self._glyphs.headers.filesystem

    @property
    def refresh_button_label(self) -> str:
        return self._language_manager["main.explorer.label.refresh_button"]

    @property
    def refresh_status_message(self) -> str:
        return self._language_manager["main.explorer.message.status_refresh"]

    def _setup_handlers(self) -> None:
        self._node_handlers = self._create_file_system_handlers(
            on_directory_clicked=self._on_directory_node_clicked,
            on_file_clicked=self._on_file_node_clicked,
            on_file_double_clicked=self._on_file_node_double_clicked,
            file_status_message=self._create_status_bar_message_function_for_file_node(),
        )

        super()._setup_handlers()

    def _create_tree_root(self) -> None:
        self._create_tree_root_heading(self.section_label)

    def _refresh_model(self) -> None:
        self._explorer_logic.refresh_tree()

    def _on_collapse_all_clicked(self) -> None:
        """Folds every folder away and drops the children it had loaded, so opening one reads it again.

        The rows fold while the model still states them, and the folders the model held go afterwards,
        which is what makes a later open list the folder as it stands on disk.
        """
        super()._on_collapse_all_clicked()
        self._explorer_logic.collapse_all()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_node_subtree(
        self,
        node: FileSystemNode,
        node_tag: str,
    ) -> None:
        self._launch_rebuild(
            lambda: None,
            lambda: self._collect_subtree_specs(node, node_tag),
            root_tag=node_tag,
        )

    def _collect_subtree_specs(
        self,
        node: FileSystemNode,
        node_tag: str,
    ) -> List[NodeSpec]:
        self._pending_specs = []
        if self._explorer_logic.has_loaded_children(node.filepath):
            for child in node.children:
                self._build_tree_node(
                    child,
                    TreeNodeState(
                        parent=node_tag,
                        has_favorite_ancestor=self._logic.has_favorite_ancestor(child),
                    ),
                )

        return self._pending_specs

    @traverse(TreeTraversal.BFS)
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, FileSystemNode):
            return

        self._mark_favorite_ancestry(node, state)

        if node.node_type == NodeType.DIRECTORY:
            self._append_spec(
                node,
                node_tag,
                state.parent,
                open_on_double_click=True,
                should_expand=self._should_expand_node(node) or self._explorer_logic.is_directory_open(node.filepath),
                has_favorite_ancestor=state.has_favorite_ancestor,
            )
        else:
            self._append_spec(
                node,
                node_tag,
                state.parent,
                leaf=True,
                has_favorite_ancestor=state.has_favorite_ancestor,
            )

        state.parent = node_tag

    def _create_status_bar_message_function_for_file_node(
        self,
    ) -> MessageCallback:
        reconstruction_message_function = self._create_status_bar_message_function_for_reconstruction_node()
        library_message_function = self._create_status_bar_message_function_for_library_node()
        audio_message_function = self._create_status_bar_message_function_for_audio_node()

        def message_function(
            *args: Any,
            user_data: Tuple[FileSystemNode, str],
            **kwargs: Any,
        ) -> str:
            node, _ = user_data
            suffix = node.filepath.suffix.lower()
            match suffix:
                case extensions.EXT_FILE_RECONSTRUCTION:
                    return reconstruction_message_function(
                        *args,
                        user_data=user_data,
                        **kwargs,
                    )
                case extensions.EXT_FILE_LIBRARY:
                    return library_message_function(
                        *args,
                        user_data=user_data,
                        **kwargs,
                    )
                case suffix if suffix in extensions.EXT_FILES_AUDIO:
                    return audio_message_function(
                        *args,
                        user_data=user_data,
                        **kwargs,
                    )
                case _:
                    raise ValueError(f"Unsupported file type {suffix} for status bar message function.")

        return message_function

    def _on_file_node_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case extensions.EXT_FILE_RECONSTRUCTION:
                    return self._logic.request_autoplay(node)
                case suffix if suffix in extensions.EXT_FILES_AUDIO:
                    self.call(self.on_wave_file_clicked, node.filepath)
                    return self._logic.request_autoplay(node)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_file_context_menu(node)

        return None

    def _on_file_node_double_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case extensions.EXT_FILE_RECONSTRUCTION:
                    self._load_reconstruction(node)
                case suffix if suffix in extensions.EXT_FILES_AUDIO:
                    self._logic.cancel_autoplay()
                    return self._reconstruct_file(node)
                case extensions.EXT_FILE_LIBRARY:
                    return self._load_library(node)

        return None

    def _on_directory_node_clicked(
        self,
        _sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, node_tag = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            return self._directory_node_clicked(node, node_tag)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(node)

        return None

    def _create_status_bar_message_function_for_audio_node(
        self,
    ) -> MessageCallback:
        def message_function(*_args: Any, **_kwargs: Any) -> str:
            if self._logic.autoplay_enabled:
                return self._language_manager["main.explorer.message.status_node_audio"]

            return self._language_manager["main.explorer.message.status_node_audio_no_autoplay"]

        return self._create_status_bar_message_function(message_function)

    def _directory_node_clicked(
        self,
        node: FileSystemNode,
        node_tag: str,
    ) -> None:
        """Answers a click on a folder: Ctrl offers its recordings to a stems list, else it opens.

        The modifier reaches the stems list only while one is being gathered, so a Ctrl-click with
        nothing to gather into opens the folder the way a plain click does.
        """
        has_content = self._explorer_logic.has_relevant_content(node.filepath)
        if not has_content:
            return

        if Modifier.CTRL in capture_modifiers() and self.query(self.can_add_stems, default=False):
            self.call(self.on_directory_add_requested, node.filepath)
            return

        self._toggle_directory_expansion(node, node_tag)
        self.call(self.on_directory_clicked, node.filepath)

    def _load_reconstruction(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if filepath.exists():
            self.call(self.on_load_reconstruction, filepath)

    def _load_library(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if filepath.exists():
            self.call(self.on_load_library, filepath)

    def _has_relevant_content(self, node: TreeNode) -> bool:
        if isinstance(node, FileSystemNode):
            return self._explorer_logic.has_relevant_content(node.filepath)

        return True

    def _reconstruct_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        self.call(self.on_reconstruct_file, node.filepath)

    def _toggle_directory_expansion(
        self,
        node: FileSystemNode,
        node_tag: str,
    ) -> None:
        """Folds or unfolds a folder, reading its children the first time it is opened.

        The folder is told what it now stands as, which is the shape a refresh and a later run of the
        application bring it back in.
        """
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        if not dpg.does_item_exist(node_tag):
            return

        is_open = not dpg.get_value(node_tag)
        if not self._explorer_logic.has_loaded_children(node.filepath):
            self._explorer_logic.expand_directory(node)
            self._rebuild_node_subtree(node, node_tag)

        dpg.set_value(node_tag, is_open)
        self._explorer_logic.set_directory_open(node.filepath, is_open)

    def _add_context_menu_file_actions(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        suffix = node.filepath.suffix.lower()
        match suffix:
            case extensions.EXT_FILE_RECONSTRUCTION:
                dpg.add_menu_item(
                    label=self._language_manager["main.explorer.label.context_load_reconstruction"],
                    callback=lambda: self._load_reconstruction(node),
                )
            case extensions.EXT_FILE_LIBRARY:
                dpg.add_menu_item(
                    label=self._language_manager["main.explorer.label.context_load_library"],
                    callback=lambda: self._load_library(node),
                )
            case suffix if suffix in extensions.EXT_FILES_AUDIO:
                dpg.add_menu_item(
                    label=self._language_manager["main.explorer.label.context_reconstruct_file"],
                    callback=lambda: self._context_reconstruct_file(node),
                )
                dpg.add_menu_item(
                    label=self._language_manager["main.explorer.label.context_add_stem"],
                    callback=lambda: self.call(self.on_file_add_requested, node.filepath),
                )

    def _show_file_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_play_item(node)
            self._add_context_menu_file_actions(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)

    def _add_context_menu_reconstruction_directory(
        self,
        node: FileSystemNode,
    ) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["main.explorer.label.context_reconstruct_directory"],
            callback=lambda: self._context_reconstruct_directory(node),
        )
        dpg.add_menu_item(
            label=self._language_manager["main.explorer.label.context_add_folder_stems"],
            callback=lambda: self.call(self.on_directory_add_requested, node.filepath),
        )

    def _add_context_menu_set_directory_items(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["main.explorer.label.context_set_output_directory"],
            callback=lambda: self._context_set_as_output_directory(node),
        )

        dpg.add_menu_item(
            label=self._language_manager["main.explorer.label.context_set_library_directory"],
            callback=lambda: self._context_set_as_library_directory(node),
        )

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        with context_menu():
            self._add_context_menu_text(node)
            self._add_context_menu_reconstruction_directory(node)
            self._add_context_menu_path_items(node.filepath)
            self._add_context_menu_favorite_item(node)
            self._add_context_menu_set_directory_items(node)

    def _context_reconstruct_file(self, node: FileSystemNode) -> None:
        self.call(self.on_reconstruct_file, node.filepath)

    def _context_reconstruct_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_reconstruct_directory, node.filepath)

    def _context_set_as_output_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_reconstructions_directory, node.filepath)

    def _context_set_as_library_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_library_directory, node.filepath)
