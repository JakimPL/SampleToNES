import threading
from typing import Any, Callable, Dict, Optional, Union

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager
from sampletones.constants import paths
from sampletones.exceptions import CallbackQueueStop
from sampletones.reconstructions import Reconstruction
from sampletones.tree import FileSystemNode, NodeType, Tree, TreeNode
from sampletones.typehints import MessageCallback, Sender
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...constants.general import (
    COL_PATH_TEXT_HOVER,
    COL_TEXT_FAVORITE,
    DIM_BUTTON_WIDTH_SEARCH,
    DIM_INPUT_WIDTH_SEARCH,
    LBL_BUTTON_TREE_CLEAR_SEARCH,
    LBL_TREE_SEARCH,
    MSG_STATUS_NODE_DIRECTORY,
    MSG_STATUS_NODE_RECONSTRUCTION,
    MSG_TREE_NO_RESULTS_FOUND,
    SUF_BUTTON_SEARCH,
    SUF_NODE_HANDLER,
    SUF_TREE_SEARCH_INPUT,
    VAL_CHARACTER_STAR,
    VAL_DELAY_SCHEDULE,
    VAL_PRIORITY_ADD_HANDLER,
    VAL_PRIORITY_ADD_NODE,
    VAL_PRIORITY_SCHEDULE,
    VAL_TEXT_COLLAPSE,
    VAL_TEXT_EXPAND,
)
from ...constants.main import (
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_MARK_AS_FAVORITE,
    LBL_CONTEXT_ITEM_MAIN_EXPLORER_UNMARK_AS_FAVORITE,
    MSG_STATUS_NODE_MAIN_EXPLORER_LIBRARY,
)
from ...themes.default import DefaultTheme
from ...themes.nodes.favorite import FavoriteChildNodeTheme, FavoriteNodeTheme
from ...themes.nodes.file import (
    LibraryFileNodeTheme,
    NoContentFileNodeTheme,
    NotExpandedDirectoryNodeTheme,
    ReconstructionFileNodeTheme,
    WaveFileNodeTheme,
)
from ...themes.nodes.library import (
    LibraryGeneratorNodeTheme,
    LibraryGroupNodeTheme,
    LibraryInstructionNodeTheme,
    LibraryLibraryNodeTheme,
)
from ...themes.theme import Theme
from ...utils.callbacks.queue import CallbackQueue
from ...utils.dpg import dpg_delete_children, dpg_delete_item, dpg_get_value
from ...utils.shortcuts.manager import ShortcutManager
from ..button import GUIButton
from ..fonts.font import Font
from ..fonts.registry import FontRegistry
from ..panel import GUIPanel
from ..status import GUIStatusBar
from .handler import Handler, ItemClickCallback
from .state import TreeNodeState


class GUITreePanel(GUIPanel):
    def __init__(
        self,
        tree: Tree,
        tag: str,
        parent: str,
        tree_tag: str,
        application_config_manager: ApplicationConfigManager,
        audio_device_manager: AudioDeviceManager,
        shortcut_manager: ShortcutManager,
        width: int = -1,
        height: int = -1,
        search_label: str = LBL_TREE_SEARCH,
    ) -> None:
        self.tree = tree
        self.tree_tag = tree_tag
        self.application_config_manager = application_config_manager
        self.audio_device_manager = audio_device_manager
        self.shortcut_manager = shortcut_manager

        self._selected_node_tag: Optional[Union[str, int]] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None

        self._pending_query: Optional[str] = None
        self._pending_autoplay_node: Optional[FileSystemNode] = None

        self._lock_counter: int = 0
        self._lock: bool = False
        self._thread_lock = threading.RLock()
        self._handler_lock = threading.Lock()

        self._handlers: Dict[str, Handler] = {}

        self.search_label = search_label

        super().__init__(
            tag=tag,
            parent=parent,
            width=width,
            height=height,
        )

    def build_tree(self, root_tag: Optional[str] = None) -> None:
        if root_tag is None:
            root_tag = self.tree_tag

        self._clear_children(root_tag)
        root = self.tree.get_root()
        if root is None:
            if self.tree.is_filtered():
                dpg.add_text(MSG_TREE_NO_RESULTS_FOUND, parent=root_tag)
            return

        self._build_tree_node(root, state=TreeNodeState(parent=root_tag))

    def create_search(self, parent: str) -> None:
        self._search_input_tag = f"{self.tag}{SUF_TREE_SEARCH_INPUT}"
        self._search_button_tag = f"{self.tag}{SUF_BUTTON_SEARCH}"

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=self.search_label,
                callback=self._on_search_changed,
                width=DIM_INPUT_WIDTH_SEARCH,
            )
            GUIButton(
                label=LBL_BUTTON_TREE_CLEAR_SEARCH,
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=DIM_BUTTON_WIDTH_SEARCH,
            )

        self.shortcut_manager.setup_input_focus_handlers(self._search_input_tag)

    def _add_node(
        self,
        node: TreeNode,
        node_tag: str,
        parent: str,
        leaf: bool = False,
        open_on_arrow: bool = False,
        open_on_double_click: bool = False,
        should_expand: bool = False,
        has_favorite_ancestor: bool = False,
        is_node_expanded: bool = False,
        item_click_callback: Optional[ItemClickCallback] = None,
        item_double_click_callback: Optional[ItemClickCallback] = None,
        status_bar_callback: Optional[MessageCallback] = None,
    ) -> None:
        with dpg.tree_node(
            label=node.name,
            tag=node_tag,
            parent=parent,
            default_open=should_expand,
            open_on_arrow=open_on_arrow,
            open_on_double_click=open_on_double_click,
            leaf=leaf,
        ):
            self._apply_node_theme(
                node_tag,
                node,
                has_favorite_ancestor=has_favorite_ancestor,
                is_node_expanded=is_node_expanded,
            )

    def _queue_node(
        self,
        node: TreeNode,
        node_tag: str,
        parent: str,
        leaf: bool = False,
        open_on_arrow: bool = False,
        open_on_double_click: bool = False,
        should_expand: bool = False,
        has_favorite_ancestor: bool = False,
        is_node_expanded: bool = False,
        item_click_callback: Optional[ItemClickCallback] = None,
        item_double_click_callback: Optional[ItemClickCallback] = None,
        status_bar_callback: Optional[MessageCallback] = None,
        add_node_priority: int = VAL_PRIORITY_ADD_NODE,
        add_handler_priority: int = VAL_PRIORITY_ADD_HANDLER,
    ) -> None:
        CallbackQueue.add(
            self._add_node,
            node,
            node_tag,
            parent,
            leaf=leaf,
            open_on_arrow=open_on_arrow,
            open_on_double_click=open_on_double_click,
            should_expand=should_expand,
            has_favorite_ancestor=has_favorite_ancestor,
            is_node_expanded=is_node_expanded,
            item_click_callback=item_click_callback,
            item_double_click_callback=item_double_click_callback,
            status_bar_callback=status_bar_callback,
            priority=add_node_priority,
        )

        CallbackQueue.add(
            self._add_item_handler_registry,
            node_tag=node_tag,
            node=node,
            item_click_callback=item_click_callback,
            item_double_click_callback=item_double_click_callback,
            status_bar_callback=status_bar_callback,
            priority=add_handler_priority,
        )

    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _has_relevant_content(self, node: TreeNode) -> bool:
        raise NotImplementedError("Subclasses must implement this method")

    def _should_expand_node(self, node: TreeNode) -> bool:
        if not self.tree.is_filtered():
            return False

        for descendant in node.descendants:
            if self.tree.is_node_visible(descendant):
                return True

        return False

    def _get_handler_registry_tag(self, tag: str) -> str:
        return f"{tag}{SUF_NODE_HANDLER}"

    def _delete_item_handler_registries(self) -> None:
        with self._handler_lock:
            for handler in self._handlers.values():
                dpg_delete_item(handler.tag)

            self._handlers.clear()

    def _assign_item_handler_registry(self, handler: Handler) -> None:
        try:
            with self._handler_lock:
                self._create_item_handler_registry(handler)
                self._bind_item_handler_registry(handler)
        except SystemError as exception:
            logger.error_with_traceback(exception, f"Error assigning item handler registry '{handler.tag}'")
            raise CallbackQueueStop(str(exception)) from exception

    def _create_item_handler_registry(self, handler: Handler) -> None:
        dpg_delete_item(handler.tag)
        with dpg.item_handler_registry(tag=handler.tag):
            if handler.item_click_callback is not None:
                item_click_callback = handler.item_click_callback
                status_bar_callback = handler.status_bar_callback

                def single_click_callback(sender: Sender, app_data: Any, user_data: Any) -> None:
                    item_click_callback(
                        sender,
                        app_data,
                        user_data,
                    )
                    if status_bar_callback is not None:
                        GUIStatusBar.set(status_bar_callback)

                dpg.add_item_clicked_handler(
                    callback=single_click_callback,
                    user_data=(handler.node, handler.parent),
                )
            if handler.item_double_click_callback is not None:
                dpg.add_item_double_clicked_handler(
                    callback=handler.item_double_click_callback,
                    user_data=(handler.node, handler.parent),
                )

        self._handlers[handler.tag] = handler

    def _bind_item_handler_registry(self, handler: Handler) -> None:
        if dpg.does_item_exist(handler.parent) and dpg.does_item_exist(handler.tag):
            dpg.bind_item_handler_registry(handler.parent, handler.tag)

    def _add_item_handler_registry(
        self,
        node_tag: str,
        node: TreeNode,
        item_click_callback: Optional[ItemClickCallback] = None,
        item_double_click_callback: Optional[ItemClickCallback] = None,
        status_bar_callback: Optional[MessageCallback] = None,
    ) -> None:
        tag = self._get_handler_registry_tag(node_tag)
        handler = Handler(
            tag=tag,
            parent=node_tag,
            node=node,
            item_click_callback=item_click_callback,
            item_double_click_callback=item_double_click_callback,
            status_bar_callback=status_bar_callback,
        )
        self._assign_item_handler_registry(handler)

    def _create_status_bar_message_function(
        self,
        message_or_function: Union[str, MessageCallback],
    ) -> MessageCallback:
        return GUIStatusBar.create_message_function(message_or_function)

    def _create_status_bar_message_function_for_reconstruction_node(self) -> MessageCallback:
        return self._create_status_bar_message_function(MSG_STATUS_NODE_RECONSTRUCTION)

    def _create_status_bar_message_function_for_library_node(self) -> MessageCallback:
        return self._create_status_bar_message_function(MSG_STATUS_NODE_MAIN_EXPLORER_LIBRARY)

    def _create_status_bar_message_function_for_directory_node(self, node_tag: str) -> MessageCallback:
        def message_function() -> str:
            return MSG_STATUS_NODE_DIRECTORY.format(
                expand_or_collapse=VAL_TEXT_COLLAPSE if dpg_get_value(node_tag) else VAL_TEXT_EXPAND,
            )

        return self._create_status_bar_message_function(message_function)

    def _generate_node_tag(self, node: TreeNode) -> str:
        path_parts = [ancestor.name for ancestor in node.path]
        tag = f"{self.tag}_node_{'_'.join(path_parts)}"
        return tag.replace(" ", "_").lower()

    def _add_context_menu_text(self, node: TreeNode) -> None:
        is_favorite = self._is_node_favorite(node)
        color = COL_TEXT_FAVORITE if is_favorite else COL_PATH_TEXT_HOVER

        with dpg.group(horizontal=True):
            if is_favorite:
                star = chr(VAL_CHARACTER_STAR)
                star_text = dpg.add_text(star, color=color)
                FontRegistry.bind_to_item(star_text, Font.ICON)

            text = dpg.add_text(node.name, color=color)
            FontRegistry.bind_to_item(text, Font.BOLD)

    def _add_context_menu_favorite_item(self, node: FileSystemNode) -> None:
        label = (
            LBL_CONTEXT_ITEM_MAIN_EXPLORER_UNMARK_AS_FAVORITE
            if self._is_node_favorite(node)
            else LBL_CONTEXT_ITEM_MAIN_EXPLORER_MARK_AS_FAVORITE
        )
        dpg.add_menu_item(
            label=label,
            callback=lambda: self._context_mark_as_favorite(node),
        )

    def _delete_children(self, tag: str) -> None:
        for child in dpg.get_item_children(tag, 1) or []:
            child_tag = dpg.get_item_alias(child)
            self._delete_children(child_tag)

            registry_tag = self._get_handler_registry_tag(child_tag)
            dpg_delete_item(registry_tag)
            if registry_tag in self._handlers:
                del self._handlers[registry_tag]

            dpg_delete_item(child_tag)

    def clear_selection(self) -> None:
        if self._selected_node_tag is not None and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)

        self._selected_node_tag = None

    def _on_search_changed(self, sender: Sender, query: str) -> None:
        if query:
            self.apply_filter(query, self._default_search_predicate)
        else:
            self.clear_filter()

        CallbackQueue.add(
            self._schedule_update_tree_visibility,
            query,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _on_clear_search_clicked(self) -> None:
        if self._search_input_tag is not None:
            dpg.set_value(self._search_input_tag, "")

        self.clear_filter()

        CallbackQueue.add(
            self._schedule_update_tree_visibility,
            "",
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _default_search_predicate(self, node: TreeNode, query: str) -> bool:
        return query.lower() in node.name.lower()

    def _rebuild_tree(self) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _update_tree_visibility(self) -> None:
        root = self.tree.get_root()
        if root is None:
            return

        for child in root.children:
            self._update_node_visibility_recursive(child)

    def _update_node_visibility_recursive(self, node: TreeNode) -> None:
        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        is_visible = self.tree.is_node_visible(node)
        dpg.configure_item(node_tag, show=is_visible)

        for child in node.children:
            self._update_node_visibility_recursive(child)

    def apply_filter(self, query: str, predicate: Callable[[TreeNode, str], bool]) -> None:
        self.tree.apply_filter(query, predicate)

    def clear_filter(self) -> None:
        self.tree.clear_filter()

    def _clear_children(self, tag: str) -> None:
        dpg_delete_children(tag)

    def _is_node_favorite(self, node: TreeNode) -> bool:
        if not isinstance(node, FileSystemNode):
            return False

        return node.filepath in self.application_config_manager.favorites

    def _has_favorite_ancestor(self, node: FileSystemNode) -> bool:
        current_node = node.parent
        while current_node is not None:
            if not isinstance(current_node, FileSystemNode):
                break

            if self._is_node_favorite(current_node):
                return True

            current_node = current_node.parent

        return False

    def _toggle_favorite(self, node: FileSystemNode) -> None:
        self.application_config_manager.toggle_favorite(node.filepath)

    def _apply_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
        has_favorite_ancestor: bool = False,
        is_node_expanded: bool = False,
    ) -> None:
        FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)
        if isinstance(node, FileSystemNode):
            match node.node_type:
                case NodeType.DIRECTORY:
                    return self._apply_directory_node_theme(
                        node_tag,
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                    )

                case NodeType.FILE:
                    return self._apply_file_node_theme(
                        node_tag,
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                        is_not_expanded=is_node_expanded,
                    )

        return self._apply_other_node_theme(node_tag, node)

    def _apply_directory_node_theme(
        self,
        node_tag: str,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
    ) -> None:
        has_content = self._has_relevant_content(node)
        is_favorite = self._is_node_favorite(node)

        theme: Theme
        if is_favorite:
            theme = FavoriteNodeTheme()
        elif not has_content:
            theme = NoContentFileNodeTheme()
        elif has_favorite_ancestor:
            theme = FavoriteChildNodeTheme()
        else:
            theme = DefaultTheme()

        theme.bind_to_item(node_tag)

    def _apply_file_node_theme(
        self,
        node_tag: str,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
        is_not_expanded: bool = False,
    ) -> None:
        is_favorite = self._is_node_favorite(node)

        theme: Theme
        if is_favorite:
            theme = FavoriteNodeTheme()
        else:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    theme = ReconstructionFileNodeTheme()
                case paths.EXT_FILE_LIBRARY:
                    theme = LibraryFileNodeTheme()
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    theme = WaveFileNodeTheme()
                case _:
                    if has_favorite_ancestor:
                        theme = FavoriteChildNodeTheme()
                    elif is_not_expanded:
                        theme = NotExpandedDirectoryNodeTheme()
                    else:
                        theme = DefaultTheme()

        theme.bind_to_item(node_tag)

    def _apply_other_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
    ) -> None:
        theme: Theme
        match node.node_type:
            case NodeType.LIBRARY:
                theme = LibraryLibraryNodeTheme()
            case NodeType.GENERATOR:
                theme = LibraryGeneratorNodeTheme()
            case NodeType.GROUP:
                theme = LibraryGroupNodeTheme()
            case NodeType.INSTRUCTION:
                theme = LibraryInstructionNodeTheme()
            case _:
                theme = DefaultTheme()

        theme.bind_to_item(node_tag)

    def _reapply_theme_recursively(self, node: FileSystemNode, has_favorite_ancestor: bool = False) -> None:
        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        self._apply_node_theme(
            node_tag,
            node,
            has_favorite_ancestor=has_favorite_ancestor,
        )
        if node.node_type == NodeType.DIRECTORY:
            is_favorite = self._is_node_favorite(node)
            child_has_favorite_ancestor = has_favorite_ancestor or is_favorite

            for child in node.children:
                if isinstance(child, FileSystemNode):
                    self._reapply_theme_recursively(
                        child,
                        has_favorite_ancestor=child_has_favorite_ancestor,
                    )

    def _context_mark_as_favorite(self, node: TreeNode) -> None:
        if not isinstance(node, FileSystemNode):
            return

        self._toggle_favorite(node)
        self._update_favorite_indicator(node)

    def _update_favorite_indicator(self, node: FileSystemNode) -> None:
        has_favorite_ancestor = self._has_favorite_ancestor(node)
        self._reapply_theme_recursively(node, has_favorite_ancestor)

    def _set_tree_enabled(self, enabled: bool) -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def _schedule_update_tree_visibility(self, query: str) -> None:
        self._pending_query = query
        CallbackQueue.add(
            self._execute_update_tree_visibility,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _execute_update_tree_visibility(self) -> None:
        if self._pending_query is not None:
            self._pending_query = None
            self._update_tree_visibility()

    def _schedule_autoplay(self, node: FileSystemNode) -> None:
        self._pending_autoplay_node = node
        CallbackQueue.add(
            self._execute_autoplay,
            priority=VAL_PRIORITY_SCHEDULE,
            delay=VAL_DELAY_SCHEDULE,
        )

    def _autoplay_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        if self.application_config_manager.autoplay:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    try:
                        reconstruction = Reconstruction.load(node.filepath)
                        self.audio_device_manager.play(reconstruction.approximation)
                    except Exception as error:
                        logger.error(f"Failed to autoplay reconstruction file: {error}")
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    self.audio_device_manager.play_file(node.filepath)

    def _execute_autoplay(self) -> None:
        if self._pending_autoplay_node is not None:
            self._autoplay_file(self._pending_autoplay_node)
            self._pending_autoplay_node = None

    def lock(self) -> None:
        with self._thread_lock:
            self._lock_counter += 1
            self._lock = True
            self._set_tree_enabled(False)

    def unlock(self) -> None:
        with self._thread_lock:
            self._lock_counter -= 1
            if self._lock_counter <= 0:
                self._lock_counter = 0
                self._lock = False
                self._set_tree_enabled(True)

    @property
    def locked(self) -> bool:
        with self._thread_lock:
            return self._lock
