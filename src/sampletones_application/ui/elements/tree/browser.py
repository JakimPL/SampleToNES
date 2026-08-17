from abc import ABC, abstractmethod

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
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.elements.tree.tree import GUITreePanel
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.parallelization.thread import concurrent
from sampletones_core.structures.tree import Tree


class GUIFileBrowserPanel(GUITreePanel, ABC):
    """Shared skeleton of a panel offering a tree of files as a collapsible, searchable card.

    The card holds a refresh control above the search box and the tree it filters. This base builds
    that arrangement, rebuilds the tree off the main thread on demand, and enables or disables the
    whole card as the tree locks and unlocks. A subclass names its widgets through
    :class:`FileBrowserTags`, states what its card and its refresh control read, answers what
    refreshing the model means, and shapes each row.
    """

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        tags: FileBrowserTags,
        scheduling: SchedulingBehavior,
        search_label: str,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
    ) -> None:
        self._tags = tags

        super().__init__(
            tree=tree,
            tag=tags.panel,
            tree_tag=tags.tree,
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
        self.rebuild_tree()

    def _create_controls(self) -> None:
        with dpg.group(tag=self._tags.group_controls):
            GUIButton(
                tag=self._tags.button_refresh,
                label=self.refresh_button_label,
                width=-1,
                callback=self.rebuild_tree,
                theme=ThemeRegistry.get(TAG_GLOBAL_THEME_SECONDARY_BUTTON),
            )

        self._status_bar.bind_to_item(
            self._tags.button_refresh,
            self.refresh_status_message,
        )

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

    def refresh(self) -> None:
        self.rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def rebuild_tree(self) -> None:
        self._launch_rebuild(
            self._refresh_model,
            lambda: self._collect_specs(self.tree_tag),
            root_tag=self.tree_tag,
        )

    @abstractmethod
    def _refresh_model(self) -> None:
        """Brings the model the tree renders up to date, on the background rebuild worker."""

    def set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(self._tags.group_tree, enabled=enabled)
        dpg_configure_item(self._tags.group_controls, enabled=enabled)
