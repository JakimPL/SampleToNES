from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior import SchedulingBehavior
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
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
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_THEME,
    TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR,
    TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP,
    TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.context_menu import add_play_menu_item
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.emitter import TreeEmitter
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_get_value,
    dpg_is_item_hovered,
)
from sampletones_application.utils.gui.tooltip import (
    create_detail_tooltip,
    populate_detail_tooltip,
)
from sampletones_application.utils.parallelization.thread import (
    BackgroundWorkCancelled,
    SingleThreadExecutor,
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
    VoidCallback,
)
from sampletones_shared.utils.system.paths import open_path_in_explorer


class GUITreePanel(GUIPanel, ABC):
    _NAME_FONT: Font = Font.REGULAR_SMALL
    _CONFIG_FONT: Font = Font.MONO_SMALL
    _MONOSPACE_CONFIG_NODES: bool = False

    def __init__(
        self,
        tree: Tree,
        tag: str,
        tree_tag: str,
        tree_logic: TreeLogicProtocol,
        width: int = -1,
        height: int = -1,
        *,
        scheduling: SchedulingBehavior,
        search_label: str,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
    ) -> None:
        self._language_manager = language_manager
        self._logic = tree_logic
        self._status_bar = status_bar
        self._scheduling = scheduling
        self.tree = tree
        self.tree_tag = tree_tag

        self._pending_specs: List[NodeSpec] = []
        self._emitter = TreeEmitter(scheduling=scheduling)

        self._selected_node_tag: Optional[Union[str, int]] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None

        self._detail_tooltip_tag = compose_tag(tag, SUF_TOOLTIP_DETAIL)
        self._detail_tooltip_handler_tag = compose_tag(tag, SUF_HANDLER_DETAIL_TOOLTIP)
        self._detail_tooltip_owner_tag: Optional[str] = None

        self._node_handlers: Dict[NodeType, NodeHandler] = {}

        self.search_label = search_label

        self._colors = colors

        self._lbl_detail_sample_rate = language_manager["global.context.label.detail_sample_rate"]
        self._lbl_detail_nes_frequency = language_manager["global.context.label.detail_nes_frequency"]
        self._lbl_detail_spectrum_method = language_manager["global.context.label.detail_spectrum_method"]
        self._lbl_detail_transformation_gamma = language_manager["global.context.label.detail_transformation_gamma"]
        self._lbl_detail_window_size = language_manager["global.context.label.detail_window_size"]
        self._lbl_detail_generators = language_manager["global.context.label.detail_generators"]
        self._lbl_detail_configuration = language_manager["global.context.label.detail_configuration"]

        self.on_add_to_sequencer: Optional[PathCallback] = None
        self.can_add_to_sequencer: Optional[Callable[[], bool]] = None
        self.on_replace_in_sequencer: Optional[PathCallback] = None
        self.replace_in_sequencer_label: Optional[Callable[[], Optional[str]]] = None
        self.on_locate_original_audio: Optional[PathCallback] = None

        super().__init__(
            tag=tag,
            width=width,
            height=height,
        )

    def _launch_rebuild(
        self,
        refresh: VoidCallback,
        collect: Callable[[], List[NodeSpec]],
        *,
        root_tag: str,
        on_finished: Optional[VoidCallback] = None,
    ) -> None:
        """Rebuild the subtree under ``root_tag``: prepare it off-thread, emit it on the main thread.

        Runs on the background traversal worker and walks through five steps:

        1. A rebuild already in flight holds the lock, so return and let it finish.
        2. Acquire the lock; responsibility for releasing it passes to the emit pipeline.
        3. ``refresh`` updates the model, then ``collect`` resolves it into a flat
           :class:`NodeSpec` list -- every per-node decision, including the filesystem
           content check, happens here on the worker.
        4. Post the specs to :class:`TreeEmitter` through the queue. This crosses back to
           the main thread, where the emitter clears the old tree and stages the new nodes
           across frames.
        5. :meth:`_finish_emit` runs as the emitter's completion callback: it applies the
           active filter, runs ``on_finished``, and releases the lock.

        A failure before the handoff releases the lock so the tree stays interactive.
        """
        if self.locked:
            return

        self.lock()
        handed_off = False
        try:
            refresh()
            specs = collect()
            CallbackQueue.add(
                self._emitter.emit,
                tuple(specs),
                root_tag,
                partial(self._finish_emit, root_tag, on_finished),
                priority=self._scheduling.emit.priority,
            )
            handed_off = True
        finally:
            if not handed_off:
                self.unlock()

    def _collect_specs(self, root_tag: str) -> List[NodeSpec]:
        """Traverse the model into a flat spec list, doing all per-node work off the main thread."""
        self._pending_specs = []
        root = self.tree.get_root()
        if root is not None:
            self._build_tree_node(root, state=TreeNodeState(parent=root_tag))

        return self._pending_specs

    def create_search(self, parent: str) -> None:
        self._search_input_tag = compose_tag(self.tag, SUF_INPUT_SEARCH)
        self._search_button_tag = compose_tag(self.tag, SUF_BUTTON_SEARCH)

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_input_text(
                tag=self._search_input_tag,
                hint=self.search_label,
                callback=self._on_search_changed,
                width=-80,
            )
            GUIButton(
                label=self._language_manager["global.browser.label.clear_search"],
                tag=self._search_button_tag,
                callback=self._on_clear_search_clicked,
                width=-1,
            )

        self._status_bar.bind_to_item(
            self._search_input_tag,
            self._language_manager["global.status.message.tree_search"],
        )
        self._status_bar.bind_to_item(
            self._search_button_tag,
            self._language_manager["global.status.message.clear_search"],
        )

    def _get_node_handler_tag(self, node_type: NodeType) -> str:
        return compose_tag(self.tag, node_type.value, SUF_HANDLER_NODE)

    def _append_spec(
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
        """Resolve a node into a :class:`NodeSpec` and record it for emission.

        Runs on the background traversal worker, so the theme and handler tags — including the
        directory content check that touches the filesystem — are chosen here, off the main
        thread. A shutdown request raises to unwind the traversal promptly.
        """
        if SingleThreadExecutor.is_shutting_down():
            raise BackgroundWorkCancelled

        theme_tag = self._resolve_node_theme_tag(
            node,
            has_favorite_ancestor=has_favorite_ancestor,
            is_node_expanded=is_node_expanded,
        )
        self._pending_specs.append(
            NodeSpec(
                node=node,
                node_tag=node_tag,
                parent_tag=parent,
                label=node.name,
                name_font=self._resolve_node_name_font(node),
                leaf=leaf,
                open_on_arrow=open_on_arrow,
                open_on_double_click=open_on_double_click,
                should_expand=should_expand,
                theme_tag=theme_tag,
                handler_tag=self._node_handlers[node.node_type].tag,
            )
        )

    def _finish_emit(self, root_tag: str, on_finished: Optional[VoidCallback]) -> None:
        """Complete a rebuild on the main thread: show the empty state, run the hook, unlock.

        The emitter runs this once its last batch has attached. When a filtered tree
        resolved to an empty model, the no-results message fills the cleared tree so the
        filter outcome is visible. Applying the filter here lets late-emitted nodes honour
        an active search, and releasing the lock hands control back to interactive rebuilds.
        """
        if root_tag == self.tree_tag and self.tree.is_filtered() and self.tree.get_root() is None:
            dpg.add_text(self._language_manager["global.dialog.message.tree_no_results"], parent=root_tag)

        if on_finished is not None:
            on_finished()

        if self.tree.is_filtered():
            self.update_tree_visibility()

        self.unlock()

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

        The reveal is gated on a change of owning node, so the tooltip content is rebuilt once per
        node.
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
                return self._language_manager["global.status.message.node_reconstruction"]

            return self._language_manager["global.status.message.node_reconstruction_no_autoplay"]

        return self._create_status_bar_message_function(message_function)

    def _create_status_bar_message_function_for_library_node(
        self,
    ) -> MessageCallback:
        return self._create_status_bar_message_function(self._language_manager["global.status.message.node_library"])

    def _create_status_bar_message_function_for_directory_node(
        self,
    ) -> MessageCallback:
        def message_function(*args: Any, user_data: Tuple[FileSystemNode, str], **kwargs: Any) -> str:
            _, node_tag = user_data
            expand_or_collapse = (
                self._language_manager["global.dialog.template.collapse"]
                if dpg_get_value(node_tag)
                else self._language_manager["global.dialog.template.expand"]
            )
            return self._language_manager["global.status.message.node_directory"].format(
                expand_or_collapse=expand_or_collapse
            )

        return self._create_status_bar_message_function(message_function)

    def _generate_node_tag(self, node: TreeNode) -> str:
        path_parts = [ancestor.name for ancestor in node.path]
        return compose_tag(self.tag, f"node_{'_'.join(path_parts)}")

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

    def _resolve_node_name_font(self, node: TreeNode) -> Font:
        """Select the label font for a node: monospace for config-bearing nodes where the panel opts in.

        A config-bearing node carries the machine-generated fields a reconstruction or library
        directory encodes, so a panel that sets ``_MONOSPACE_CONFIG_NODES`` renders those names in
        the fixed-width font for legibility. Every other node keeps the panel's ``_NAME_FONT``.
        """
        if self._MONOSPACE_CONFIG_NODES and self._node_detail_items(node):
            return self._CONFIG_FONT

        return self._NAME_FONT

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
            FontRegistry.bind_to_item(detail_text, Font.MONO_SMALL)

    def _add_context_menu_play_item(self, node: FileSystemNode) -> None:
        if not self._logic.is_playable_file(node):
            return

        dpg.add_separator()
        add_play_menu_item(self._language_manager["global.context.label.play"], lambda: self._logic.play_node(node))

    def _add_context_menu_path_items(self, path: Path) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["global.context.label.copy_filename"],
            callback=lambda: dpg.set_clipboard_text(str(path.name)),
        )
        dpg.add_menu_item(
            label=self._language_manager["global.context.label.copy_path"],
            callback=lambda: dpg.set_clipboard_text(str(path)),
        )
        dpg.add_menu_item(
            label=self._language_manager["global.context.label.open_in_explorer"],
            callback=lambda: open_path_in_explorer(path),
        )

    def _add_context_menu_sequencer_items(self, node: FileSystemNode) -> None:
        """Add the send-to-sequencer item, live while its host reports the sequencer accepts one."""
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["global.context.label.add_to_sequencer"],
            callback=self._on_add_to_sequencer,
            user_data=node,
            enabled=self.query(self.can_add_to_sequencer, default=False),
        )

    def _add_context_menu_replace_item(self, node: FileSystemNode) -> None:
        """Add the replace-in-sequencer item, naming the sample this file would overwrite.

        The target is whichever sample the sequencer has selected, so the item is present while a
        selection names one and its label is read fresh on each right-click. Carrying no separator
        groups it with the add item a caller places above it, since both push this file into the
        sequencer.
        """
        target = self.query(self.replace_in_sequencer_label, default=None)
        if target is None:
            return

        dpg.add_menu_item(
            label=self._language_manager["global.context.template.replace_sample"].format(sample=target),
            callback=self._on_replace_in_sequencer,
            user_data=node,
        )

    def _add_context_menu_locate_audio_item(self, node: FileSystemNode) -> None:
        dpg.add_menu_item(
            label=self._language_manager["global.context.label.locate_original_audio"],
            callback=self._on_locate_original_audio,
            user_data=node,
        )

    def _on_locate_original_audio(self, sender: Sender, app_data: Any, user_data: FileSystemNode) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_locate_original_audio, user_data.filepath)

    def _add_context_menu_favorite_item(self, node: FileSystemNode) -> None:
        label = (
            self._language_manager["global.context.label.unmark_as_favorite"]
            if self._logic.is_node_favorite(node)
            else self._language_manager["global.context.label.mark_as_favorite"]
        )
        dpg.add_separator()
        dpg.add_menu_item(
            label=label,
            callback=lambda: self._context_mark_as_favorite(node),
        )

    def _on_add_to_sequencer(self, sender: Sender, app_data: Any, user_data: FileSystemNode) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_add_to_sequencer, user_data.filepath)

    def _on_replace_in_sequencer(self, sender: Sender, app_data: Any, user_data: FileSystemNode) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_replace_in_sequencer, user_data.filepath)

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

    def _apply_node_theme(
        self,
        node_tag: str,
        node: TreeNode,
        has_favorite_ancestor: bool = False,
        is_node_expanded: bool = False,
    ) -> None:
        FontRegistry.bind_to_item(node_tag, self._resolve_node_name_font(node))
        theme_tag = self._resolve_node_theme_tag(
            node,
            has_favorite_ancestor=has_favorite_ancestor,
            is_node_expanded=is_node_expanded,
        )
        ThemeRegistry.get(theme_tag).bind_to_item(node_tag)

    def _resolve_node_theme_tag(
        self,
        node: TreeNode,
        *,
        has_favorite_ancestor: bool = False,
        is_node_expanded: bool = False,
    ) -> str:
        """Select the theme tag for a node from its type, favorite state, and content.

        Pure lookup that touches no DearPyGui, so the background traversal can resolve it into
        each :class:`NodeSpec`; the main-thread emitter binds the chosen theme by tag.
        """
        if isinstance(node, FileSystemNode):
            match node.node_type:
                case NodeType.DIRECTORY:
                    return self._resolve_directory_theme_tag(node, has_favorite_ancestor=has_favorite_ancestor)
                case NodeType.FILE:
                    return self._resolve_file_theme_tag(
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                        is_not_expanded=is_node_expanded,
                    )

        return self._resolve_other_theme_tag(node)

    def _resolve_directory_theme_tag(
        self,
        node: FileSystemNode,
        *,
        has_favorite_ancestor: bool = False,
    ) -> str:
        if self._logic.is_node_favorite(node):
            return TAG_GLOBAL_THEME_FAVORITE

        if not self._has_relevant_content(node):
            return TAG_GLOBAL_THEME_FILE_NO_CONTENT

        if has_favorite_ancestor:
            return TAG_GLOBAL_THEME_FAVORITE_CHILD

        return TAG_GLOBAL_THEME_DEFAULT

    def _resolve_file_theme_tag(
        self,
        node: FileSystemNode,
        *,
        has_favorite_ancestor: bool = False,
        is_not_expanded: bool = False,
    ) -> str:
        if self._logic.is_node_favorite(node):
            return TAG_GLOBAL_THEME_FAVORITE

        match node.filepath.suffix.lower():
            case paths.EXT_FILE_RECONSTRUCTION:
                return TAG_GLOBAL_THEME_FILE_RECONSTRUCTION
            case paths.EXT_FILE_LIBRARY:
                return TAG_GLOBAL_THEME_FILE_LIBRARY
            case suffix if suffix in paths.EXT_FILES_AUDIO:
                return TAG_GLOBAL_THEME_FILE_WAVE
            case _:
                if has_favorite_ancestor:
                    return TAG_GLOBAL_THEME_FAVORITE_CHILD
                if is_not_expanded:
                    return TAG_GLOBAL_THEME_FILE_NOT_EXPANDED_DIRECTORY
                return TAG_GLOBAL_THEME_DEFAULT

    def _resolve_other_theme_tag(self, node: TreeNode) -> str:
        match node.node_type:
            case NodeType.LIBRARY:
                return TAG_INSTRUCTIONS_LIBRARY_THEME
            case NodeType.GENERATOR:
                return TAG_INSTRUCTIONS_LIBRARY_THEME_GENERATOR
            case NodeType.GROUP:
                return TAG_INSTRUCTIONS_LIBRARY_THEME_GROUP
            case NodeType.INSTRUCTION:
                return TAG_INSTRUCTIONS_LIBRARY_THEME_INSTRUCTION
            case _:
                return TAG_GLOBAL_THEME_DEFAULT

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
