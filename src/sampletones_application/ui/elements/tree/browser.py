from abc import ABC, abstractmethod
from typing import Dict

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.general import TAG_GLOBAL_THEME_SECONDARY_BUTTON
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.layout.collapse import CollapseAxis
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.handler import NodeHandler
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.state import TreeNodeState
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.structures.tree import FileSystemNode, NodeType, Tree
from sampletones_shared.types.callback import Callback, MessageCallback, VoidCallback


class GUIFileBrowserPanel(GUITreePanel, ABC):
    """Shared skeleton of a panel offering a tree of files as a collapsible, searchable card.

    The card holds a refresh control above the search box and the tree it filters. This base builds
    that arrangement, rebuilds the tree off the main thread on demand, and enables or disables the
    whole card as the tree locks and unlocks. A subclass declares its widgets as a
    :class:`FileBrowserTags`, states what its card and its refresh control read, answers what
    refreshing the model means, and shapes each row.
    """

    _REBUILD_ON_CREATE: bool = True

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        search_label: str,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
    ) -> None:
        super().__init__(
            tree=tree,
            tag=self._tags.panel,
            tree_tag=self._tags.tree,
            tree_logic=tree_logic,
            scheduling=scheduling,
            search_label=search_label,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
        )

        self._enable_horizontal_collapse(
            initial_collapsed=initial_collapsed,
            side=CollapseAxis.HORIZONTAL_LEFT,
        )

    @property
    @abstractmethod
    def _tags(self) -> FileBrowserTags:
        """The tags naming this browser's widgets, which a panel states as a class attribute."""

    @property
    @abstractmethod
    def section_label(self) -> str: ...

    @property
    @abstractmethod
    def section_glyph(self) -> str: ...

    @property
    @abstractmethod
    def refresh_button_label(self) -> str: ...

    @property
    @abstractmethod
    def refresh_status_message(self) -> str: ...

    def create_panel(self, parent: str) -> None:
        """Builds the card, and fills the tree where the panel is the one reading its model.

        A browser reading the filesystem shows its rows as it appears, while a catalogue filled by
        the owner that gathers it waits for that reading to arrive.
        """
        self._setup_handlers()
        with (
            dpg.child_window(
                tag=self.tag,
                width=self.width,
                height=self.height,
                parent=parent,
                border=False,
            ),
            self._collapsible_section(
                self.section_label,
                glyph=self.section_glyph,
            ),
        ):
            self._create_controls()
            dpg.add_separator()
            self._create_tree_window()

        self._create_detail_tooltip(self._tags.window_tree)
        if self._REBUILD_ON_CREATE:
            self.rebuild_tree()

    def _create_controls(self) -> None:
        with dpg.group(tag=self._tags.group_controls):
            self._create_refresh_button()

        self._bind_refresh_message()

    def _create_refresh_button(self) -> None:
        GUIButton(
            tag=self._tags.button_refresh,
            label=self.refresh_button_label,
            width=-1,
            callback=self._on_refresh_clicked,
            theme=ThemeRegistry.get(TAG_GLOBAL_THEME_SECONDARY_BUTTON),
        )

    def _bind_refresh_message(self) -> None:
        self._status_bar.bind_to_item(
            self._tags.button_refresh,
            self.refresh_status_message,
        )

    def _on_refresh_clicked(self) -> None:
        """Answers the refresh control, by default with a rebuild of the tree as the model stands."""
        self.rebuild_tree()

    def _create_tree_window(self) -> None:
        self.create_search(self._body_container)
        with (
            dpg.child_window(
                tag=self._tags.window_tree,
                horizontal_scrollbar=True,
            ),
            dpg.group(tag=self._tags.group_tree),
        ):
            self._create_tree_root()

    def _create_tree_root(self) -> None:
        """Opens the container every row attaches to, as a group the rows read directly under."""
        with dpg.group(tag=self.tree_tag):
            pass

    def _create_tree_root_heading(self, label: str) -> None:
        """Opens the root container as a labelled row the whole tree folds under."""
        with dpg.tree_node(
            label=label,
            tag=self.tree_tag,
            default_open=True,
        ):
            pass

    def _create_file_system_handlers(
        self,
        *,
        on_directory_clicked: Callback,
        on_file_clicked: Callback,
        on_file_double_clicked: Callback,
        file_status_message: MessageCallback,
    ) -> Dict[NodeType, NodeHandler]:
        """The two rows a browser of files offers: a folder that expands, and a file it opens.

        A folder row reads the same wherever it appears — the status bar says it expands — so the pair
        is shaped here, and each browser states what a click on one of its own rows means.
        """
        return {
            NodeType.DIRECTORY: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.DIRECTORY),
                node_type=NodeType.DIRECTORY,
                item_click_callback=on_directory_clicked,
                status_bar_callback=self._create_status_bar_message_function_for_expandable_node(),
            ),
            NodeType.FILE: NodeHandler(
                tag=self._get_node_handler_tag(NodeType.FILE),
                node_type=NodeType.FILE,
                item_click_callback=on_file_clicked,
                item_double_click_callback=on_file_double_clicked,
                status_bar_callback=file_status_message,
            ),
        }

    def _mark_favorite_ancestry(
        self,
        node: FileSystemNode,
        state: TreeNodeState,
    ) -> None:
        """Carries a favorite down the branch, so every row under one reads as part of it."""
        state.has_favorite_ancestor |= self._logic.is_node_favorite(node) or self._logic.has_favorite_ancestor(node)

    def refresh(self) -> None:
        self.rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def rebuild_tree(self) -> None:
        self._launch_tree_rebuild(self._refresh_model)

    @concurrent(wait=False, method_bound=True)
    def redraw_tree(self) -> None:
        self._launch_tree_rebuild(self._keep_model)

    def _launch_tree_rebuild(self, refresh: VoidCallback) -> None:
        """Fills the whole tree from the model ``refresh`` leaves behind, off the main thread."""
        self._launch_rebuild(
            refresh,
            lambda: self._collect_specs(self.tree_tag),
            root_tag=self.tree_tag,
            on_finished=self._on_rebuild_finished,
        )

    @abstractmethod
    def _refresh_model(self) -> None:
        """Brings the model the tree renders up to date, on the background rebuild worker."""

    def _keep_model(self) -> None:
        """Leaves the model as the last refresh brought it, which is what a redraw reads."""

    def _on_rebuild_finished(self) -> None:
        """Runs on the main thread with the rows on screen, where a browser reads something out."""

    def set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(self._tags.group_tree, enabled=enabled)
        dpg_configure_item(self._tags.group_controls, enabled=enabled)
