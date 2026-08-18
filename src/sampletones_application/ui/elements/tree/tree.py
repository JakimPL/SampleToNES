from abc import ABC, abstractmethod
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_SEARCH,
    SUF_CHECKBOX_FAVORITES,
    SUF_HANDLER_DETAIL_TOOLTIP,
    SUF_HANDLER_NODE,
    SUF_INPUT_SEARCH,
    SUF_TEXT_FAVORITES,
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
from sampletones_application.ui.elements.context_menu import (
    add_detail_items,
    add_play_menu_item,
)
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.elements.panel import GUIPanel
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.emitter import TreeEmitter
from sampletones_application.ui.elements.tree.filter import NO_FILTER, TreeFilter
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.spec import NodeSpec
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tag import compose_node_tag
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_application.utils.gui.dpg import (
    dpg_configure_item,
    dpg_get_value,
    dpg_is_item_hovered,
    dpg_set_value,
)
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.tooltip import (
    create_detail_tooltip,
    populate_detail_tooltip,
)
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.parallelization.thread import (
    BackgroundWorkCancelled,
    SingleThreadExecutor,
)
from sampletones_core.configs.display import (
    format_nes_frequency,
    format_sample_rate,
    format_spectrum_method,
    short_hash,
)
from sampletones_core.library import InstructionLibraryKey
from sampletones_core.reconstructions.converter.paths import ConfigDirectoryFields
from sampletones_core.structures.tree import (
    ConfigNode,
    FileSystemNode,
    LibraryNode,
    NodeType,
    Tree,
    TreeNode,
    TreeVisibility,
    resolve_visibility,
)
from sampletones_shared.paths import extensions
from sampletones_shared.types.application import Sender
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
    _REMEMBERS_EXPANSION: bool = False

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
        self._expanded_rows: Set[str] = set()
        self._emitter = TreeEmitter(scheduling=scheduling)

        self._filter: TreeFilter = NO_FILTER
        self._search_visibility: Optional[TreeVisibility] = None
        self._favorites_visibility: Optional[TreeVisibility] = None
        self._favorites_anchors: Optional[TreeVisibility] = None

        self._selected_node_tag: Optional[Union[str, int]] = None
        self._search_input_tag: Optional[str] = None
        self._search_button_tag: Optional[str] = None
        self._favorites_checkbox_tag: Optional[str] = None
        self._favorites_glyph_tag: Optional[str] = None

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

        self.on_favorites_filter_changed: Optional[Callable[[str, bool], None]] = None
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
        3. ``refresh`` updates the model and the filter is resolved against it, then
           ``collect`` resolves it into a flat :class:`NodeSpec` list -- every per-node
           decision, including the filesystem content check, happens here on the worker.
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
            self._resolve_filter()
            specs = collect()
            CallbackQueue.add(
                self._emitter.emit,
                tuple(specs),
                root_tag,
                partial(
                    self._finish_emit,
                    root_tag,
                    on_finished,
                    len(specs),
                ),
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

        self._forget_rows_the_model_dropped()
        return self._pending_specs

    def _forget_rows_the_model_dropped(self) -> None:
        """Holds the memory of open rows to the rows a pass over the whole tree found.

        A pass showing everything states which rows exist, so a row it left out belongs to a folder
        the disk no longer holds and its place in the memory goes with it. A pass narrowed to the
        favorites speaks for those rows alone, and leaves the memory of the rest as it stands.
        """
        if not self._REMEMBERS_EXPANSION or self._filter.favorites_only:
            return

        self._expanded_rows &= {spec.node_tag for spec in self._pending_specs}

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

    def create_favorites_filter(self, parent: str) -> None:
        """Builds the control showing the favorites alone, as a row of its own under the search box.

        The checkbox carries the label, so the words are part of what the reader clicks, and the star
        beside it reads in the colour the mode it stands for is drawn in. The label reads in the pair
        every checkbox reads — the text colour while the control is live, the muted one while a
        rebuild holds it — so the shade states whether the control can be acted on.
        """
        self._favorites_checkbox_tag = compose_tag(self.tag, SUF_CHECKBOX_FAVORITES)
        self._favorites_glyph_tag = compose_tag(self.tag, SUF_TEXT_FAVORITES)

        with dpg.group(horizontal=True, parent=parent):
            dpg.add_checkbox(
                tag=self._favorites_checkbox_tag,
                label=self._language_manager["global.browser.label.favorites_only"],
                default_value=self._filter.favorites_only,
                callback=self._on_favorites_only_changed,
            )
            dpg.add_text(
                self._glyphs.common.favorite,
                tag=self._favorites_glyph_tag,
            )

        FontRegistry.bind_to_item(self._favorites_glyph_tag, Font.ICON)
        self._apply_favorites_glyph_color()
        self._status_bar.bind_to_item(
            self._favorites_checkbox_tag,
            self._language_manager["global.status.message.favorites_only"],
        )

    def _on_favorites_only_changed(
        self,
        _sender: Sender,
        favorites_only: bool,
    ) -> None:
        """Takes the mode the control now reads, and draws the rows that mode names.

        The rebuild resolves the filter against the model as it collects the rows, so the mode is
        stated here and answered there, and turning it on walks the model once.
        """
        self._filter = self._filter.with_favorites_only(favorites_only)
        self._apply_favorites_glyph_color()
        self.call(
            self.on_favorites_filter_changed,
            self.tag,
            favorites_only,
        )
        self.redraw_tree()

    def _apply_favorites_glyph_color(self) -> None:
        """Colours the star by the mode the control reads, wherever the browser offers one."""
        if self._favorites_glyph_tag is None:
            return

        dpg_set_palette_color(self._favorites_glyph_tag, self._favorites_glyph_color())

    def _favorites_glyph_color(self) -> BaseColor:
        """The colour the star takes: the favorite colour while the mode is on, muted while it is off."""
        if self._filter.favorites_only:
            return self._colors.favorite

        return self._colors.muted

    def set_favorites_filter_enabled(self, enabled: bool) -> None:
        """Follows the tree's lock through to the control, which asks for a rebuild of that tree."""
        if self._favorites_checkbox_tag is None:
            return

        dpg_configure_item(self._favorites_checkbox_tag, enabled=enabled)

    def _restore_favorites_only(self, favorites_only: bool) -> None:
        """Takes the mode a session left the browser in, which its first rebuild then draws by."""
        self._filter = self._filter.with_favorites_only(favorites_only)

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

        Which rows are recorded is the favorites mode's to state, and it shows a row together with
        every row above it: a row it holds back therefore stands above rows it holds back too, so one
        decision covers the whole subtree and the traversal walks on.
        """
        if SingleThreadExecutor.is_shutting_down():
            raise BackgroundWorkCancelled

        if not self._is_node_drawn(node):
            return

        theme_tag = self._resolve_node_theme_tag(
            node,
            has_favorite_ancestor=has_favorite_ancestor,
            is_node_expanded=is_node_expanded,
        )
        stands_open = self._stands_open(
            node,
            node_tag,
            should_expand=should_expand,
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
                should_expand=stands_open,
                theme_tag=theme_tag,
                handler_tag=self._node_handlers[node.node_type].tag,
            )
        )

    def _stands_open(
        self,
        node: TreeNode,
        node_tag: str,
        *,
        should_expand: bool,
    ) -> bool:
        """Whether the row is created standing open: the filter points at it, or the memory holds it.

        The shape the reader built is theirs to keep, so a row they opened comes back open and the
        filter adds the way down to what it names. Recording the answer here is what carries that
        shape into the pass after this one.
        """
        if not self._REMEMBERS_EXPANSION:
            return should_expand

        stands_open = should_expand or node_tag in self._expanded_rows
        self._set_row_expanded(node_tag, stands_open and bool(node.children))
        return stands_open

    def _set_row_expanded(self, node_tag: str, expanded: bool) -> None:
        """Holds whether a row stands open, which is what a later pass brings it back by."""
        if expanded:
            self._expanded_rows.add(node_tag)
            return

        self._expanded_rows.discard(node_tag)

    def _set_subtree_expanded(self, node: TreeNode, *, expanded: bool) -> None:
        """Folds or unfolds the row together with every row below it holding something.

        Each row is reached by the tag it was built under and set directly, and the browser is told
        what it now stands as, so a rebuild brings the whole subtree back the way this left it.
        """
        for container in (node, *node.descendants):
            if container.children:
                node_tag = self._generate_node_tag(container)
                dpg_set_value(node_tag, expanded)
                self._set_row_expanded(node_tag, expanded)

    def _finish_emit(
        self,
        root_tag: str,
        on_finished: Optional[VoidCallback],
        drawn_rows: int,
    ) -> None:
        """Complete a rebuild on the main thread: show the empty state, run the hook, unlock.

        The emitter runs this once its last batch has attached. A filtered rebuild that drew no
        row fills the cleared tree with the message naming that outcome, so the filter's answer is
        legible where the rows would be. Applying the filter here lets late-emitted nodes honour
        an active search, and releasing the lock hands control back to interactive rebuilds.
        """
        if root_tag == self.tree_tag and self._filter.is_active and not drawn_rows:
            dpg.add_text(
                self._empty_filter_message(),
                parent=root_tag,
            )

        if on_finished is not None:
            on_finished()

        if self._filter.query:
            self.update_tree_visibility()

        self.unlock()

    def _empty_filter_message(self) -> str:
        """Names the filter a rebuild came back empty from: the favorites mode, or the search."""
        return self._language_manager[
            (
                "global.dialog.message.tree_no_favorites"
                if self._filter.favorites_only
                else "global.dialog.message.tree_no_results"
            )
        ]

    def _create_hover_callback(
        self,
        status_bar_callback: Optional[MessageCallback],
    ) -> Callback:
        def hover_callback(
            _sender: Sender,
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

    def _on_detail_tooltip_mouse_move(
        self,
        _sender: Sender,
        _app_data: Any,
    ) -> None:
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
            self._remember_clicked_row(user_data)
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
                item_double_click_callback(
                    sender,
                    app_data,
                    user_data=user_data,
                )

        return double_click_callback

    def _remember_clicked_row(self, user_data: Any) -> None:
        """Follows a click through to what it left the row standing as, a frame after it landed.

        A click on a row the reader can open is how that row folds and unfolds, and the row states
        its own answer once the frame carrying the click has drawn. Reading it the frame after
        therefore reports what the reader did, whichever button they pressed, and a row holding
        nothing has nothing to remember.
        """
        if not self._REMEMBERS_EXPANSION or not isinstance(user_data, tuple):
            return

        node, node_tag = user_data
        if not node.children:
            return

        CallbackQueue.add(
            self._read_row_expansion,
            node_tag,
            delay=1,
        )

    def _read_row_expansion(self, node_tag: str) -> None:
        """Takes the state a row stands in into the memory, on the main thread that owns the row."""
        if not dpg.does_item_exist(node_tag):
            return

        self._set_row_expanded(node_tag, bool(dpg_get_value(node_tag)))

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
        """Whether the row is emitted standing open, which a row leading to a named row is.

        A search result and a favorite are both what the reader is looking for, so the way down to
        either one opens and the filter's answer reads at a glance. What each criterion names is the
        row the reader is pointed at rather than everything that row brings along, so a folder opens
        to show what it holds while the rows inside it stand as they are.
        """
        return any(
            visibility.should_expand(node)
            for visibility in (self._search_visibility, self._favorites_anchors)
            if visibility is not None
        )

    def _create_status_bar_message_function(
        self,
        message_or_function: Union[str, MessageCallback],
    ) -> MessageCallback:
        return GUIStatusBar.create_message_function(message_or_function)

    def _create_status_bar_message_function_for_reconstruction_node(
        self,
    ) -> MessageCallback:
        def message_function(*_args: Any, **_kwargs: Any) -> str:
            if self._logic.autoplay_enabled:
                return self._language_manager["global.status.message.node_reconstruction"]

            return self._language_manager["global.status.message.node_reconstruction_no_autoplay"]

        return self._create_status_bar_message_function(message_function)

    def _create_status_bar_message_function_for_library_node(
        self,
    ) -> MessageCallback:
        return self._create_status_bar_message_function(self._language_manager["global.status.message.node_library"])

    def _create_status_bar_message_function_for_expandable_node(
        self,
    ) -> MessageCallback:
        """Builds the hover message of a row the reader opens, naming what that row holds.

        A folder, a group and a sample are all opened the same way and hold different things, so the
        message follows the node it is asked about: the sample names the reconstructions it gathers.
        """

        def message_function(
            *_args: Any,
            user_data: Tuple[TreeNode, str],
            **_kwargs: Any,
        ) -> str:
            node, node_tag = user_data
            expand_or_collapse = (
                self._language_manager["global.dialog.template.collapse"]
                if dpg_get_value(node_tag)
                else self._language_manager["global.dialog.template.expand"]
            )
            return self._expandable_node_message(node).format(expand_or_collapse=expand_or_collapse)

        return self._create_status_bar_message_function(message_function)

    def _expandable_node_message(self, node: TreeNode) -> str:
        match node.node_type:
            case NodeType.SAMPLE:
                return self._language_manager["global.status.message.node_sample"]
            case NodeType.GROUP:
                return self._language_manager["global.status.message.node_group"]

        return self._language_manager["global.status.message.node_directory"]

    def _generate_node_tag(self, node: TreeNode) -> str:
        return compose_node_tag(node, panel_tag=self.tag)

    def _context_menu_header_name(self, node: TreeNode) -> str:
        """Returns the raw on-disk identifier, complementing the friendly label shown in the tree."""
        match node:
            case LibraryNode():
                return Path(node.library_key.filename).stem
            case FileSystemNode():
                return node.filepath.name

        return str(node.name)

    def _node_header_color(self, node: TreeNode) -> BaseColor:
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
                star_text = dpg.add_text(self._glyphs.common.favorite)
                dpg_set_palette_color(star_text, color)
                FontRegistry.bind_to_item(star_text, Font.ICON)

            text = dpg.add_text(self._context_menu_header_name(node))
            dpg_set_palette_color(text, color)
            FontRegistry.bind_to_item(text, Font.BOLD)

    def _node_detail_items(self, node: TreeNode) -> List[Tuple[str, str]]:
        match node:
            case LibraryNode():
                return self._library_detail_items(node.library_key)
            case ConfigNode():
                return self._reconstruction_detail_items(node.config)

        return []

    def _library_detail_items(
        self,
        key: InstructionLibraryKey,
    ) -> List[Tuple[str, str]]:
        nes_frequency = round(key.sample_rate / key.frame_length)
        return [
            (self._lbl_detail_sample_rate, format_sample_rate(key.sample_rate)),
            (self._lbl_detail_nes_frequency, format_nes_frequency(nes_frequency)),
            (self._lbl_detail_spectrum_method, format_spectrum_method(key.spectrum_method)),
            (self._lbl_detail_transformation_gamma, str(key.transformation_gamma)),
            (self._lbl_detail_window_size, str(key.window_size)),
            (self._lbl_detail_configuration, short_hash(key.config_hash)),
        ]

    def _reconstruction_detail_items(
        self,
        fields: ConfigDirectoryFields,
    ) -> List[Tuple[str, str]]:
        generators = ", ".join(
            generator.capitalized for generator in fields.generators
        )  # TODO: operation deserves a helper function
        return [
            (self._lbl_detail_sample_rate, format_sample_rate(fields.sr)),
            (self._lbl_detail_nes_frequency, format_nes_frequency(fields.nf)),
            (self._lbl_detail_spectrum_method, format_spectrum_method(fields.sm)),
            (self._lbl_detail_transformation_gamma, str(fields.tg)),
            (self._lbl_detail_generators, generators),
            (self._lbl_detail_configuration, short_hash(fields.ch)),
        ]

    def _add_context_menu_details(self, node: TreeNode) -> None:
        add_detail_items(
            self._node_detail_items(node),
            color=self._colors.muted,
        )

    def _add_context_menu_play_item(self, node: FileSystemNode) -> None:
        if not self._logic.is_playable_file(node):
            return

        dpg.add_separator()
        add_play_menu_item(
            self._language_manager["global.context.label.play"],
            lambda: self._logic.play_node(node),
        )

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

    def _on_locate_original_audio(
        self,
        _sender: Sender,
        _app_data: Any,
        user_data: FileSystemNode,
    ) -> None:
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

    def _on_add_to_sequencer(
        self,
        _sender: Sender,
        _app_data: Any,
        user_data: FileSystemNode,
    ) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_add_to_sequencer, user_data.filepath)

    def _on_replace_in_sequencer(
        self,
        _sender: Sender,
        _app_data: Any,
        user_data: FileSystemNode,
    ) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NodeType.FILE:
            return

        self.call(self.on_replace_in_sequencer, user_data.filepath)

    def _on_search_changed(self, _sender: Sender, query: str) -> None:
        self._set_query(query)

    def _on_clear_search_clicked(self) -> None:
        if self._search_input_tag is not None:
            dpg.set_value(self._search_input_tag, "")

        self._set_query("")

    def _set_query(self, query: str) -> None:
        """Take the query the browser is now asked to show, and resolve the rows it names.

        The rows already drawn are the favorites mode's to state, so a keystroke resolves the search
        alone and the tree on screen answers the one after it.
        """
        self._filter = self._filter.with_query(query)
        self._search_visibility = self._resolve_search_visibility()
        self._logic.schedule_search_update(query)

    def _resolve_filter(self) -> None:
        """Resolve the filter against the model as it stands, which a rebuild does once per pass.

        Reading the model rather than the rows lets the resolution run on the rebuild worker, and
        keeps a filter typed before a refresh answering for the rows that refresh brings.
        """
        self._search_visibility = self._resolve_search_visibility()
        (
            self._favorites_visibility,
            self._favorites_anchors,
        ) = self._resolve_favorites()

    def _resolve_search_visibility(self) -> Optional[TreeVisibility]:
        """The rows the search query names, and nothing to narrow by while no query is typed."""
        query = self._filter.query
        if not query:
            return None

        return resolve_visibility(
            self.tree.find_nodes(
                TreeNode,
                lambda node: self._default_search_predicate(node, query),
            )
        )

    def _resolve_favorites(
        self,
    ) -> Tuple[Optional[TreeVisibility], Optional[TreeVisibility]]:
        """The rows the favorites mode keeps, and the rows it points the reader at.

        The two answer different questions — which rows the browser draws, and which of them stand
        open — so each is resolved from a set of its own, the second being a part of the first. One
        walk of the model finds the rows the star reaches, and the anchors are read out of that
        answer, so a corpus of any size resolves into a walk and a pair of sets.
        """
        if not self._filter.favorites_only:
            return None, None

        reached = self.tree.find_nodes(TreeNode, self._is_node_starred)
        return (
            resolve_visibility(reached),
            resolve_visibility([node for node in reached if self._is_node_anchored(node)]),
        )

    def _is_node_starred(self, node: TreeNode) -> bool:
        """Whether the favorites mode names the row: it carries a star, or a starred folder holds it.

        Being held by a starred folder is a fact about the path, so a reconstruction listed under the
        sample it came from answers the same as the row standing for it beside its configuration.
        """
        if self._logic.is_node_favorite(node):
            return True

        return isinstance(node, FileSystemNode) and self._logic.has_favorite_ancestor(node)

    def _is_node_anchored(self, node: TreeNode) -> bool:
        """Whether the mode points the reader at the row, which is what opens the way down to it.

        A star sits on a row the reader marked, so the way to that row opens wherever it sits —
        inside another starred folder among the rest. A row a starred folder merely holds is where
        the star first reaches only while no row above it is reached, which is how the sample branch
        answers: its headings carry no path, so the variants are where the star arrives.

        Asked of the rows the star reaches, so a row it declines stands under a row it named, and
        the reader is pointed at the folder rather than at everything inside it.
        """
        if self._logic.is_node_favorite(node):
            return True

        parent = node.parent
        return parent is None or not self._is_node_starred(parent)

    def _default_search_predicate(self, node: TreeNode, query: str) -> bool:
        return query.lower() in node.name.lower()

    @abstractmethod
    def rebuild_tree(self) -> None: ...

    @abstractmethod
    def redraw_tree(self) -> None:
        """Draws the rows again from the model in hand, which a change of filter asks for."""

    def update_tree_visibility(self) -> None:
        """Show the rows the search names and hide the rest, over the rows already on screen.

        Runs on the main thread once the typing settles, so a query narrows what is drawn in place
        of asking for a rebuild.
        """
        root = self.tree.get_root()
        if root is None:
            return

        for child in root.children:
            self._update_node_visibility_recursive(child)

    def _update_node_visibility_recursive(self, node: TreeNode) -> None:
        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        dpg.configure_item(node_tag, show=self._is_node_visible(node))

        for child in node.children:
            self._update_node_visibility_recursive(child)

    def _is_node_visible(self, node: TreeNode) -> bool:
        """Whether the search shows the row, which every row on screen reads as while none is typed."""
        if self._search_visibility is None:
            return True

        return self._search_visibility.is_visible(node)

    def _is_node_drawn(self, node: TreeNode) -> bool:
        """Whether the favorites mode draws the row, which it does for every row while it is off."""
        if self._favorites_visibility is None:
            return True

        return self._favorites_visibility.is_visible(node)

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
                    return self._resolve_directory_theme_tag(
                        node,
                        has_favorite_ancestor=has_favorite_ancestor,
                    )
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
            case extensions.EXT_FILE_RECONSTRUCTION:
                return TAG_GLOBAL_THEME_FILE_RECONSTRUCTION
            case extensions.EXT_FILE_LIBRARY:
                return TAG_GLOBAL_THEME_FILE_LIBRARY
            case suffix if suffix in extensions.EXT_FILES_AUDIO:
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

    def _reapply_theme_recursively(
        self,
        node: FileSystemNode,
        has_favorite_ancestor: bool = False,
    ) -> None:
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

    def update_favorite_indicators(
        self,
        nodes: Sequence[FileSystemNode],
    ) -> None:
        """Follows a favorite change through the rows it reaches, and what each of them holds.

        A path reaches the panel as many rows as the views offer it — a reconstruction is listed both
        by its configuration and by the sample it came from — and the star belongs to the path, so
        the caller names every row standing for it and each of them takes the new theme with the
        ancestry its own path carries.

        While the mode shows the favorites alone the star decides which rows exist, so the change is
        answered by drawing the tree again from the model in hand: starring a row brings it in, and
        unstarring one takes it out along with what it held.
        """
        if self._filter.favorites_only:
            self.redraw_tree()
            return

        for node in nodes:
            self._reapply_theme_recursively(
                node,
                self._logic.has_favorite_ancestor(node),
            )

    @abstractmethod
    def set_tree_enabled(self, enabled: bool) -> None: ...

    def lock(self) -> None:
        self._logic.lock()

    def unlock(self) -> None:
        self._logic.unlock()

    @property
    def locked(self) -> bool:
        return self._logic.locked
