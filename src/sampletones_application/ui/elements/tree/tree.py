from abc import abstractmethod
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.elements.global_ import (
    ContextElements,
    GlobalMessageElements,
    GlobalTemplateElements,
    NodeDetailElements,
    StatusElements,
    TreeElements,
)
from sampletones_application.categories.hierarchy import Page, Panel, TextType
from sampletones_application.categories.key import TAG_SEPARATOR
from sampletones_application.categories.manager import LanguageManager
from sampletones_application.constants.general import (
    SUF_BUTTON_SEARCH,
    SUF_HANDLER_DETAIL_TOOLTIP,
    SUF_HANDLER_NODE,
    SUF_INPUT_SEARCH,
    SUF_TOOLTIP_DETAIL,
    TAG_GLOBAL_THEME_DEFAULT,
    TAG_GLOBAL_THEME_FAVORITE,
    TAG_GLOBAL_THEME_FAVORITE_CHILD,
    TAG_GLOBAL_THEME_FILE_LIBRARY,
    TAG_GLOBAL_THEME_FILE_NO_CONTENT,
    TAG_GLOBAL_THEME_FILE_NOT_EXPANDED_DIRECTORY,
    TAG_GLOBAL_THEME_FILE_RECONSTRUCTION,
    TAG_GLOBAL_THEME_FILE_WAVE,
    TAG_GLOBAL_THEME_TREE_WINDOW,
)
from sampletones_application.constants.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR,
    TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP,
    TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION,
    TAG_INSTRUCTIONS_LIBRARY_THEME_LIBRARY,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import add_play_menu_item
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_delete_children,
    dpg_get_value,
    dpg_is_item_hovered,
)
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_application.utils.gui.tooltip import (
    create_detail_tooltip,
    populate_detail_tooltip,
)
from sampletones_core import paths
from sampletones_core.configs.display import (
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
    short_hash,
)
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import (
    FileSystemNode,
    LibraryNode,
    NodeType,
    Tree,
    TreeNode,
)
from sampletones_shared.types.application import ColorRGBA, Sender
from sampletones_shared.types.callback import (
    Callback,
    MessageCallback,
    PathCallback,
)
from sampletones_shared.utils.system.paths import open_path_in_explorer


class GUITreePanel(GUIPanel):
    def __init__(
        self,
        tree: Tree,
        tag: str,
        tree_tag: str,
        tree_logic: TreeLogicProtocol,
        shortcut_manager: ShortcutManager,
        width: int = -1,
        height: int = -1,
        *,
        search_label: str,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
    ) -> None:
        self._logic = tree_logic
        self._status_bar = status_bar
        self.tree = tree
        self.tree_tag = tree_tag
        self.shortcut_manager = shortcut_manager

        self._selected_node_tag: Optional[Union[str, int]] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None

        self._detail_tooltip_tag = f"{tag}{SUF_TOOLTIP_DETAIL}"
        self._detail_tooltip_handler_tag = f"{tag}{SUF_HANDLER_DETAIL_TOOLTIP}"
        self._detail_tooltip_owner_tag: Optional[str] = None

        self._node_handlers: Dict[NodeType, NodeHandler] = {}

        self.search_label = search_label

        self._colors = colors

        self._lbl_clear_search = language_manager[
            Page.GLOBAL,
            Panel.BROWSER,
            TextType.LABEL,
            TreeElements.CLEAR_SEARCH,
        ]
        self._msg_no_results = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.MESSAGE,
            GlobalMessageElements.TREE_NO_RESULTS,
        ]
        self._msg_tree_search = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.TREE_SEARCH,
        ]
        self._msg_node_reconstruction = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.NODE_RECONSTRUCTION,
        ]
        self._msg_node_reconstruction_no_autoplay = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.NODE_RECONSTRUCTION_NO_AUTOPLAY,
        ]
        self._msg_node_library = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.NODE_LIBRARY,
        ]
        self._template_node_directory = language_manager[
            Page.GLOBAL,
            Panel.STATUS,
            TextType.MESSAGE,
            StatusElements.NODE_DIRECTORY,
        ]
        self._msg_expand = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.EXPAND,
        ]
        self._msg_collapse = language_manager[
            Page.GLOBAL,
            Panel.DIALOG,
            TextType.TEMPLATE,
            GlobalTemplateElements.COLLAPSE,
        ]
        self._lbl_ctx_play = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.PLAY,
        ]
        self._lbl_ctx_copy_filename = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.COPY_FILENAME,
        ]
        self._lbl_ctx_copy_path = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.COPY_PATH,
        ]
        self._lbl_ctx_open_in_explorer = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.OPEN_IN_EXPLORER,
        ]
        self._lbl_ctx_add_to_sequencer = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.ADD_TO_SEQUENCER,
        ]
        self._lbl_ctx_mark_as_favorite = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.MARK_AS_FAVORITE,
        ]
        self._lbl_ctx_unmark_as_favorite = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            ContextElements.UNMARK_AS_FAVORITE,
        ]
        self._lbl_detail_sample_rate = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.SAMPLE_RATE,
        ]
        self._lbl_detail_nes_frequency = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.NES_FREQUENCY,
        ]
        self._lbl_detail_generators = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.GENERATORS,
        ]
        self._lbl_detail_spectrum_method = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.SPECTRUM_METHOD,
        ]
        self._lbl_detail_transformation_gamma = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.TRANSFORMATION_GAMMA,
        ]
        self._lbl_detail_window_size = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.WINDOW_SIZE,
        ]
        self._lbl_detail_configuration = language_manager[
            Page.GLOBAL,
            Panel.CONTEXT,
            TextType.LABEL,
            NodeDetailElements.CONFIGURATION,
        ]

        self.on_add_to_sequencer: Optional[PathCallback] = None
        self.can_add_to_sequencer: Optional[Callable[[], bool]] = None

        super().__init__(
            tag=tag,
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
                dpg.add_text(self._msg_no_results, parent=root_tag)
            return

        self._build_tree_node(root, state=TreeNodeState(parent=root_tag))

    def create_search(self, parent: str) -> None:
        self._search_input_tag = f"{self.tag}{SUF_INPUT_SEARCH}"
        self._search_button_tag = f"{self.tag}{SUF_BUTTON_SEARCH}"

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=self.search_label,
                callback=self._on_search_changed,
                width=-80,
            )
            GUIButton(
                label=self._lbl_clear_search,
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=-1,
            )

        self.shortcut_manager.setup_input_focus_handlers(self._search_input_tag)
        self._status_bar.bind_to_item(self._search_input_tag, self._msg_tree_search)

    def _get_node_handler_tag(self, node_type: NodeType) -> str:
        return f"{self.tag}{TAG_SEPARATOR}{node_type.value}{SUF_HANDLER_NODE}"

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
    ) -> None:
        if not dpg.does_item_exist(parent):
            return

        with dpg.tree_node(
            label=node.name,
            tag=node_tag,
            parent=parent,
            default_open=should_expand,
            open_on_arrow=open_on_arrow,
            open_on_double_click=open_on_double_click,
            leaf=leaf,
            bullet=leaf,
            user_data=(node, node_tag),
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
        add_node_priority: int = 5,
        add_handler_priority: int = 10,
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
            priority=add_node_priority,
        )

        CallbackQueue.add(
            self._bind_item_handler_registry,
            node_tag=node_tag,
            node=node,
            priority=add_handler_priority,
        )

    def _create_hover_callback(
        self,
        status_bar_callback: Optional[MessageCallback],
    ) -> Callback:
        def hover_callback(
            sender: Sender,
            app_data: int,
        ) -> None:
            user_data = dpg.get_item_user_data(app_data)
            if status_bar_callback is not None:
                self._status_bar.set(status_bar_callback, user_data=user_data)
            self._update_detail_tooltip(user_data)

        return hover_callback

    def _create_detail_tooltip(self, tree_window_tag: str) -> None:
        """Builds the reusable detail tooltip and the mouse handler that dismisses it.

        Binding the tooltip to the tree window keeps it visible while the pointer stays over the tree,
        and the handler clears it once the owning node's row is left, so the details track the hovered
        main node and disappear over the tree's blank space.
        """
        ThemeRegistry.get(TAG_GLOBAL_THEME_TREE_WINDOW).bind_to_item(tree_window_tag)
        create_detail_tooltip(tree_window_tag, tag=self._detail_tooltip_tag)
        with dpg.handler_registry(tag=self._detail_tooltip_handler_tag):
            dpg.add_mouse_move_handler(callback=self._on_detail_tooltip_mouse_move)

    def _update_detail_tooltip(self, user_data: Any) -> None:
        """Reveals the detail tooltip for a hovered node that carries details, hiding it otherwise.

        The reveal is gated on a change of owning node so the tooltip content is rebuilt once per node
        rather than on every hover frame.
        """
        if not isinstance(user_data, tuple):
            return

        node, node_tag = user_data
        detail_items = self._node_detail_items(node)
        if detail_items:
            if self._detail_tooltip_owner_tag != node_tag:
                populate_detail_tooltip(self._detail_tooltip_tag, detail_items)
                self._detail_tooltip_owner_tag = node_tag
                dpg_configure_item(self._detail_tooltip_tag, show=True)

            return

        self._hide_detail_tooltip()

    def _hide_detail_tooltip(self) -> None:
        if self._detail_tooltip_owner_tag is None:
            return

        self._detail_tooltip_owner_tag = None
        dpg_configure_item(self._detail_tooltip_tag, show=False)

    def _on_detail_tooltip_mouse_move(self, sender: Sender, app_data: Any) -> None:
        owner_tag = self._detail_tooltip_owner_tag
        if owner_tag is None:
            return

        if not dpg.does_item_exist(owner_tag) or not dpg_is_item_hovered(owner_tag):
            self._hide_detail_tooltip()

    def _create_single_click_callback(
        self,
        item_click_callback: Optional[Callback],
        status_bar_callback: Optional[MessageCallback],
    ) -> Callback:
        def single_click_callback(
            sender: Sender,
            app_data: Tuple[int, int],
        ) -> None:
            user_data = dpg.get_item_user_data(app_data[1])
            if item_click_callback is not None:
                item_click_callback(sender, app_data, user_data=user_data)
            if status_bar_callback is not None:
                self._status_bar.set(status_bar_callback, user_data=user_data)

        return single_click_callback

    def _create_double_click_callback(
        self,
        item_double_click_callback: Optional[Callback],
    ) -> Callback:
        def double_click_callback(
            sender: Sender,
            app_data: Tuple[int, int],
        ) -> None:
            user_data = dpg.get_item_user_data(app_data[1])
            if item_double_click_callback is not None:
                item_double_click_callback(sender, app_data, user_data=user_data)

        return double_click_callback

    def _setup_handlers(self) -> None:
        for handler in self._node_handlers.values():
            with dpg.item_handler_registry(tag=handler.tag):
                item_click_callback = handler.item_click_callback
                item_double_click_callback = handler.item_double_click_callback
                status_bar_callback = handler.status_bar_callback
                if item_click_callback is not None or status_bar_callback is not None:
                    dpg.add_item_clicked_handler(
                        callback=self._create_single_click_callback(
                            item_click_callback,
                            status_bar_callback,
                        )
                    )

                    if status_bar_callback is not None:
                        dpg.add_item_hover_handler(
                            callback=self._create_hover_callback(
                                status_bar_callback,
                            )
                        )

                if item_double_click_callback is not None:
                    dpg.add_item_double_clicked_handler(
                        callback=self._create_double_click_callback(
                            item_double_click_callback,
                        )
                    )

    def _bind_item_handler_registry(self, node_tag: str, node: TreeNode) -> None:
        handler_tag = self._node_handlers[node.node_type].tag
        if dpg.does_item_exist(node_tag) and dpg.does_item_exist(handler_tag):
            dpg.bind_item_handler_registry(node_tag, handler_tag)

    @abstractmethod
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
        **kwargs: Any,
    ) -> None: ...

    @abstractmethod
    def _has_relevant_content(self, node: TreeNode) -> bool: ...

    def _should_expand_node(self, node: TreeNode) -> bool:
        if not self.tree.is_filtered():
            return False

        for descendant in node.descendants:
            if self.tree.is_node_visible(descendant):
                return True

        return False

    def _create_status_bar_message_function(
        self,
        message_or_function: Union[str, MessageCallback],
    ) -> MessageCallback:
        return GUIStatusBar.create_message_function(message_or_function)

    def _create_status_bar_message_function_for_reconstruction_node(
        self,
    ) -> MessageCallback:
        def message_function(*args: Any, **kwargs: Any) -> str:
            if self._logic.autoplay_enabled:
                return self._msg_node_reconstruction

            return self._msg_node_reconstruction_no_autoplay

        return self._create_status_bar_message_function(message_function)

    def _create_status_bar_message_function_for_library_node(
        self,
    ) -> MessageCallback:
        return self._create_status_bar_message_function(self._msg_node_library)

    def _create_status_bar_message_function_for_directory_node(
        self,
    ) -> MessageCallback:
        def message_function(*args: Any, user_data: Tuple[FileSystemNode, str], **kwargs: Any) -> str:
            _, node_tag = user_data
            expand_or_collapse = self._msg_collapse if dpg_get_value(node_tag) else self._msg_expand
            return self._template_node_directory.format(expand_or_collapse=expand_or_collapse)

        return self._create_status_bar_message_function(message_function)

    def _generate_node_tag(self, node: TreeNode) -> str:
        path_parts = [ancestor.name for ancestor in node.path]
        tag = f"{self.tag}{TAG_SEPARATOR}node_{'_'.join(path_parts)}"
        return tag.replace(" ", "_").lower()

    def _context_menu_header_name(self, node: TreeNode) -> str:
        """Returns the raw on-disk identifier, complementing the friendly label shown in the tree."""
        match node:
            case LibraryNode():
                return Path(node.library_key.filename).stem
            case FileSystemNode():
                return node.filepath.name

        return str(node.name)

    def _node_header_color(self, node: TreeNode) -> ColorRGBA:
        if self._logic.is_node_favorite(node):
            return self._colors.favorite

        if self._node_detail_items(node):
            return self._colors.accent

        return self._colors.node

    def _add_context_menu_text(self, node: TreeNode) -> None:
        is_favorite = self._logic.is_node_favorite(node)
        color = self._node_header_color(node)

        with dpg.group(horizontal=True):
            if is_favorite:
                star_text = dpg.add_text(self._glyphs.common.favorite, color=color)
                FontRegistry.bind_to_item(star_text, Font.ICON)

            text = dpg.add_text(self._context_menu_header_name(node), color=color)
            FontRegistry.bind_to_item(text, Font.BOLD)

    def _node_detail_items(self, node: TreeNode) -> List[Tuple[str, str]]:
        match node:
            case LibraryNode():
                return self._library_detail_items(node.library_key)
            case FileSystemNode() if node.node_type == NodeType.DIRECTORY:
                return self._reconstruction_detail_items(node.filepath.name)

        return []

    def _library_detail_items(self, key: InstructionLibraryKey) -> List[Tuple[str, str]]:
        nes_frequency = round(key.sample_rate / key.frame_length)
        return [
            (self._lbl_detail_sample_rate, format_sample_rate(key.sample_rate)),
            (self._lbl_detail_nes_frequency, format_nes_frequency(nes_frequency)),
            (self._lbl_detail_spectrum_method, format_spectrum_method(key.spectrum_method)),
            (self._lbl_detail_transformation_gamma, str(key.transformation_gamma)),
            (self._lbl_detail_window_size, str(key.window_size)),
            (self._lbl_detail_configuration, short_hash(key.config_hash)),
        ]

    def _reconstruction_detail_items(self, directory_name: str) -> List[Tuple[str, str]]:
        fields = ConfigDirectoryFields.from_directory_name(directory_name)
        if fields is None:
            return []

        generators = ", ".join(generator.capitalized for generator in fields.generators)
        return [
            (self._lbl_detail_sample_rate, format_sample_rate(fields.sr)),
            (self._lbl_detail_nes_frequency, format_nes_frequency(fields.nf)),
            (self._lbl_detail_spectrum_method, format_spectrum_method(fields.sm)),
            (self._lbl_detail_transformation_gamma, str(fields.tg)),
            (self._lbl_detail_generators, generators),
            (self._lbl_detail_configuration, short_hash(fields.ch)),
        ]

    def _add_context_menu_details(self, node: TreeNode) -> None:
        detail_items = self._node_detail_items(node)
        if not detail_items:
            return

        dpg.add_separator()
        for label, value in detail_items:
            detail_text = dpg.add_text(f"{label}: {value}", color=self._colors.muted)
            FontRegistry.bind_to_item(detail_text, Font.REGULAR_SMALL)

    def _add_context_menu_play_item(self, node: FileSystemNode) -> None:
        if not self._logic.is_playable_file(node):
            return

        dpg.add_separator()
        add_play_menu_item(self._lbl_ctx_play, lambda: self._logic.play_node(node))

    def _add_context_menu_path_items(self, path: Path) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_copy_filename,
            callback=lambda: dpg.set_clipboard_text(str(path.name)),
        )
        dpg.add_menu_item(
            label=self._lbl_ctx_copy_path,
            callback=lambda: dpg.set_clipboard_text(str(path)),
        )
        dpg.add_menu_item(
            label=self._lbl_ctx_open_in_explorer,
            callback=lambda: open_path_in_explorer(path),
        )

    def _add_context_menu_sequencer_items(self, node: FileSystemNode) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._lbl_ctx_add_to_sequencer,
            callback=self._on_add_to_sequencer,
            user_data=node,
            enabled=self.call(self.can_add_to_sequencer),
        )

    def _add_context_menu_favorite_item(self, node: FileSystemNode) -> None:
        label = (
            self._lbl_ctx_unmark_as_favorite if self._logic.is_node_favorite(node) else self._lbl_ctx_mark_as_favorite
        )
        dpg.add_separator()
        dpg.add_menu_item(
            label=label,
            callback=lambda: self._context_mark_as_favorite(node),
        )

    def clear_selection(self) -> None:
        if self._selected_node_tag is not None and dpg.does_item_exist(self._selected_node_tag):
            dpg.set_value(self._selected_node_tag, False)

        self._selected_node_tag = None

    def _on_add_to_sequencer(self, sender: Sender, app_data: Any, user_data: FileSystemNode) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_add_to_sequencer, user_data.filepath)

    def _on_search_changed(self, sender: Sender, query: str) -> None:
        if query:
            self.apply_filter(query, self._default_search_predicate)
        else:
            self.clear_filter()

        self._logic.schedule_search_update(query)

    def _on_clear_search_clicked(self) -> None:
        if self._search_input_tag is not None:
            dpg.set_value(self._search_input_tag, "")

        self.clear_filter()

        self._logic.schedule_search_update("")

    def _default_search_predicate(self, node: TreeNode, query: str) -> bool:
        return query.lower() in node.name.lower()

    @abstractmethod
    def rebuild_tree(self) -> None: ...

    def update_tree_visibility(self) -> None:
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
        is_favorite = self._logic.is_node_favorite(node)

        theme: Theme
        if is_favorite:
            theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FAVORITE)
        elif not has_content:
            theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FILE_NO_CONTENT)
        elif has_favorite_ancestor:
            theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FAVORITE_CHILD)
        else:
            theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)

        theme.bind_to_item(node_tag)

    def _apply_file_node_theme(
        self,
        node_tag: str,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
        is_not_expanded: bool = False,
    ) -> None:
        is_favorite = self._logic.is_node_favorite(node)

        theme: Theme
        if is_favorite:
            theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FAVORITE)
        else:
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FILE_RECONSTRUCTION)
                case paths.EXT_FILE_LIBRARY:
                    theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FILE_LIBRARY)
                case suffix if suffix in paths.EXT_FILES_AUDIO:
                    theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FILE_WAVE)
                case _:
                    if has_favorite_ancestor:
                        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FAVORITE_CHILD)
                    elif is_not_expanded:
                        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_FILE_NOT_EXPANDED_DIRECTORY)
                    else:
                        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)

        theme.bind_to_item(node_tag)

    def _apply_other_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
    ) -> None:
        theme: Theme
        match node.node_type:
            case NodeType.LIBRARY:
                theme = ThemeRegistry.get(TAG_INSTRUCTIONS_LIBRARY_THEME_LIBRARY)
            case NodeType.GENERATOR:
                theme = ThemeRegistry.get(TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR)
            case NodeType.GROUP:
                theme = ThemeRegistry.get(TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP)
            case NodeType.INSTRUCTION:
                theme = ThemeRegistry.get(TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION)
            case _:
                theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DEFAULT)

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
            is_favorite = self._logic.is_node_favorite(node)
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

        self._logic.toggle_favorite(node)

    def update_favorite_indicator(self, node: FileSystemNode) -> None:
        has_favorite_ancestor = self._logic.has_favorite_ancestor(node)
        self._reapply_theme_recursively(node, has_favorite_ancestor)

    @abstractmethod
    def set_tree_enabled(self, enabled: bool) -> None: ...

    def lock(self) -> None:
        self._logic.lock()

    def unlock(self) -> None:
        self._logic.unlock()

    @property
    def locked(self) -> bool:
        return self._logic.locked
