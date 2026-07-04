from pathlib import Path
from typing import Any, Callable, Dict, Optional, Protocol, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import TreeElements
from sampletones_application.categories.elements.main import ExplorerElements
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_PANEL_LEFT,
    TAG_GLOBAL_TAB_MAIN,
)
from sampletones_application.constants.main import (
    TAG_MAIN_EXPLORER_BUTTON_COLLAPSE_ALL,
    TAG_MAIN_EXPLORER_BUTTON_REFRESH,
    TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
    TAG_MAIN_EXPLORER_GROUP_CONTROLS,
    TAG_MAIN_EXPLORER_GROUP_TREE,
    TAG_MAIN_EXPLORER_PANEL,
    TAG_MAIN_EXPLORER_TREE,
    TAG_MAIN_EXPLORER_WINDOW_TREE,
)
from sampletones_application.layout.behavior import TreeBehavior
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import context_menu
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.utils.gui.dialogs import DialogsRenderer
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_children,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.thread import concurrent
from sampletones_core import paths
from sampletones_core.structures.tree import (
    FileSystemNode,
    NodeType,
    Tree,
    TreeNode,
    TreeTraversal,
    traverse,
)
from sampletones_shared.logger import logger
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

    def is_directory_expanded(self, filepath: Path) -> bool: ...

    def has_relevant_content(self, filepath: Path) -> bool: ...


class GUIExplorerPanel(GUITreePanel):
    def __init__(
        self,
        explorer_logic: ExplorerLogicProtocol,
        tree_logic: TreeLogicProtocol,
        shortcut_manager: ShortcutManager,
        *,
        tree_behavior: TreeBehavior,
        language_manager: LanguageManager,
        dialogs: DialogsRenderer,
        colors: TreeColors,
    ) -> None:
        self._explorer_logic = explorer_logic
        self.shortcut_manager = shortcut_manager
        self._tree_behavior = tree_behavior
        self._dialogs = dialogs

        self._lbl_section = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.SECTION,
        ]
        self._lbl_refresh = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.REFRESH_BUTTON,
        ]
        self._lbl_collapse_all = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.COLLAPSE_ALL_BUTTON,
        ]
        self._lbl_ctx_load_reconstruction = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_LOAD_RECONSTRUCTION,
        ]
        self._lbl_ctx_load_library = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_LOAD_LIBRARY,
        ]
        self._lbl_ctx_reconstruct_file = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_RECONSTRUCT_FILE,
        ]
        self._lbl_ctx_reconstruct_directory = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_RECONSTRUCT_DIRECTORY,
        ]
        self._lbl_ctx_set_library = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_SET_LIBRARY_DIRECTORY,
        ]
        self._lbl_ctx_set_output = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.LABEL,
            ExplorerElements.CONTEXT_SET_OUTPUT_DIRECTORY,
        ]
        self._msg_converter_running = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.MESSAGE,
            ExplorerElements.CONVERTER_RUNNING_MSG,
        ]
        self._msg_status_audio_no_autoplay = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.MESSAGE,
            ExplorerElements.STATUS_NODE_AUDIO_NO_AUTOPLAY,
        ]
        self._msg_status_audio = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.MESSAGE,
            ExplorerElements.STATUS_NODE_AUDIO,
        ]
        self._ttl_converter_running = language_manager[
            Page.MAIN,
            Panel.EXPLORER,
            TextType.TITLE,
            ExplorerElements.CONVERTER_RUNNING_DIALOG,
        ]

        self._node_handlers: Dict[NodeType, NodeHandler]

        self.on_wave_file_clicked: Optional[PathCallback] = None
        self.on_directory_clicked: Optional[PathCallback] = None
        self.on_reconstruct_directory: Optional[PathCallback] = None
        self.on_reconstruct_file: Optional[PathCallback] = None
        self.on_load_reconstruction: Optional[PathCallback] = None
        self.on_load_library: Optional[PathCallback] = None
        self.on_set_as_reconstructions_directory: Optional[PathCallback] = None
        self.on_set_as_library_directory: Optional[PathCallback] = None
        self.is_converter_running: Optional[Callable[[], bool]] = None

        super().__init__(
            tree=self._explorer_logic.tree,
            tag=TAG_MAIN_EXPLORER_PANEL,
            parent=f"{TAG_GLOBAL_TAB_MAIN}{SUF_PANEL_LEFT}",
            tree_tag=TAG_MAIN_EXPLORER_TREE,
            tree_logic=tree_logic,
            shortcut_manager=shortcut_manager,
            search_label=language_manager[
                Page.GLOBAL,
                Panel.BROWSER,
                TextType.LABEL,
                TreeElements.FILTER,
            ],
            language_manager=language_manager,
            colors=colors,
        )

    def create_panel(self) -> None:
        self._setup_handlers()
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_buttons()
            self._create_tree_window()

        self._rebuild_tree()

    def _setup_handlers(self) -> None:
        self._node_handlers = {
            NodeType.DIRECTORY: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.DIRECTORY),
                node_type=NodeType.DIRECTORY,
                item_click_callback=self._on_directory_node_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_directory_node(),
            ),
            NodeType.FILE: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.FILE),
                node_type=NodeType.FILE,
                item_click_callback=self._on_file_node_clicked,
                item_double_click_callback=self._on_file_node_double_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_file_node(),
            ),
        }

        super()._setup_handlers()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(self._lbl_section)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_buttons(self) -> None:
        dpg.add_separator()
        with dpg.group(tag=TAG_MAIN_EXPLORER_GROUP_CONTROLS):
            GUIButton(
                tag=TAG_MAIN_EXPLORER_BUTTON_REFRESH,
                label=self._lbl_refresh,
                parent=self.tag,
                width=-1,
                callback=self.refresh,
            )
            GUIButton(
                tag=TAG_MAIN_EXPLORER_BUTTON_COLLAPSE_ALL,
                label=self._lbl_collapse_all,
                parent=self.tag,
                width=-1,
                callback=self.collapse_all,
            )

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_MAIN_EXPLORER_WINDOW_TREE):
            with dpg.group(tag=TAG_MAIN_EXPLORER_GROUP_TREE):
                with dpg.tree_node(
                    label=self._lbl_section,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def collapse_all(self, sender: Sender, app_data: int, user_data: object) -> None:
        self._explorer_logic.collapse_all()
        children = dpg.get_item_children(self.tree_tag, 1)
        assert children is not None, "Explorer tree has no children."
        for node_tag in children:
            dpg.set_value(node_tag, False)

    def refresh(self) -> None:
        self._rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_tree(self) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self._explorer_logic.refresh_tree()
            self.build_tree()
        finally:
            self.unlock()

    def _rebuild_directory_node(self, node: FileSystemNode, node_tag: str) -> None:
        if self.locked:
            return

        self.lock()
        try:
            self._rebuild_node_subtree(node, node_tag)
        finally:
            self.unlock()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_node_subtree(self, node: FileSystemNode, node_tag: str) -> None:
        if not dpg.does_item_exist(node_tag):
            return

        dpg_delete_children(node_tag)
        if self._explorer_logic.is_directory_expanded(node.filepath):
            for child in node.children:
                has_favorite_ancestor = self._logic.is_node_favorite(node) or self._logic.has_favorite_ancestor(child)
                self._build_tree_node(
                    child,
                    TreeNodeState(
                        parent=node_tag,
                        has_favorite_ancestor=has_favorite_ancestor,
                    ),
                )

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

        is_favorite = self._logic.is_node_favorite(node)
        state.has_favorite_ancestor |= is_favorite

        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node) or self._explorer_logic.is_directory_expanded(node.filepath)
            is_directory_expanded = self._explorer_logic.is_directory_expanded(node.filepath)
            self._queue_node(
                node,
                node_tag,
                state.parent,
                open_on_double_click=True,
                should_expand=should_expand,
                has_favorite_ancestor=state.has_favorite_ancestor,
                is_node_expanded=is_directory_expanded,
                add_node_priority=self._tree_behavior.priority_add_node,
                add_handler_priority=self._tree_behavior.priority_add_handler,
            )
        else:
            self._queue_node(
                node,
                node_tag,
                state.parent,
                leaf=True,
                has_favorite_ancestor=state.has_favorite_ancestor,
                add_node_priority=self._tree_behavior.priority_add_node,
                add_handler_priority=self._tree_behavior.priority_add_handler,
            )

        state.parent = node_tag

    def _create_status_bar_message_function_for_file_node(
        self,
    ) -> MessageCallback:
        reconstruction_message_function = self._create_status_bar_message_function_for_reconstruction_node()
        library_message_function = self._create_status_bar_message_function_for_library_node()
        audio_message_function = self._create_status_bar_message_function_for_audio_node()

        def message_function(*args: Any, user_data: Tuple[FileSystemNode, str], **kwargs: Any) -> str:
            node, _ = user_data
            suffix = node.filepath.suffix.lower()
            match suffix:
                case paths.EXT_FILE_RECONSTRUCTION:
                    return reconstruction_message_function(*args, user_data=user_data, **kwargs)
                case paths.EXT_FILE_LIBRARY:
                    return library_message_function(*args, user_data=user_data, **kwargs)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    return audio_message_function(*args, user_data=user_data, **kwargs)
                case _:
                    raise ValueError(f"Unsupported file type {suffix} for status bar message function.")

        return message_function

    def _on_file_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    return self._logic.request_autoplay(node)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    self.call(self.on_wave_file_clicked, node.filepath)
                    return self._logic.request_autoplay(node)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_file_context_menu(node)

        return None

    def _on_file_node_double_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, Sender],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    self._load_reconstruction(node)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    self._logic.cancel_autoplay()
                    return self._reconstruct_file(node)
                case paths.EXT_FILE_LIBRARY:
                    return self._load_library(node)

        return None

    def _on_directory_node_clicked(
        self,
        sender: Sender,
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
        def message_function(*args: Any, **kwargs: Any) -> str:
            if self._logic.autoplay_enabled:
                return self._msg_status_audio

            return self._msg_status_audio_no_autoplay

        return self._create_status_bar_message_function(message_function)

    def _directory_node_clicked(self, node: FileSystemNode, node_tag: str) -> None:
        has_content = self._explorer_logic.has_relevant_content(node.filepath)
        if not has_content:
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

    def set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_MAIN_EXPLORER_GROUP_TREE, enabled=enabled)
        dpg_configure_item(TAG_MAIN_EXPLORER_GROUP_CONTROLS, enabled=enabled)

    def _reconstruct_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_file, node.filepath)

    def _toggle_directory_expansion(self, node: FileSystemNode, node_tag: str) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        if not dpg.does_item_exist(node_tag):
            return

        is_directory_expanded = self._explorer_logic.is_directory_expanded(node.filepath)
        state = dpg.get_value(node_tag)
        if not is_directory_expanded:
            self._explorer_logic.expand_directory(node)
            self._rebuild_directory_node(node, node_tag)

        dpg.set_value(node_tag, not state)

    def _add_context_menu_file_actions(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        suffix = node.filepath.suffix.lower()
        match suffix:
            case paths.EXT_FILE_RECONSTRUCTION:
                dpg.add_menu_item(
                    label=self._lbl_ctx_load_reconstruction,
                    callback=lambda: self._load_reconstruction(node),
                )
            case paths.EXT_FILE_LIBRARY:
                dpg.add_menu_item(
                    label=self._lbl_ctx_load_library,
                    callback=lambda: self._load_library(node),
                )
            case suffix if suffix in paths.EXT_FILES_AUDIO:
                dpg.add_menu_item(
                    label=self._lbl_ctx_reconstruct_file,
                    callback=lambda: self._context_reconstruct_file(node),
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

    def _add_context_menu_reconstruction_directory(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_reconstruct_directory,
            callback=lambda: self._context_reconstruct_directory(node),
        )

    def _add_context_menu_reconstruction_file(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_reconstruct_file,
            callback=lambda: self._context_reconstruct_file(node),
        )

    def _add_context_menu_set_directory_items(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_set_output,
            callback=lambda: self._context_set_as_output_directory(node),
        )

        dpg.add_menu_item(
            label=self._lbl_ctx_set_library,
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

    def _check_if_converter_running(self) -> bool:
        is_running = self.call(self.is_converter_running)
        if is_running:
            logger.warning("Conversion is already running. Wait or cancel the current operation.")
            self._dialogs.show_info(
                tag=TAG_MAIN_EXPLORER_DIALOG_CONVERTER_RUNNING,
                message=self._msg_converter_running,
                title=self._ttl_converter_running,
            )
            return True

        return False

    def _context_reconstruct_file(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_file, node.filepath)

    def _context_reconstruct_directory(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        self.call(self.on_reconstruct_directory, node.filepath)

    def _context_set_as_output_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_reconstructions_directory, node.filepath)

    def _context_set_as_library_directory(self, node: FileSystemNode) -> None:
        self.call(self.on_set_as_library_directory, node.filepath)
