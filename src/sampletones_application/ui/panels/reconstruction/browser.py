from pathlib import Path
from typing import Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.behavior.scheduling.scheduling import (
    SchedulingBehavior,
)
from sampletones_application.tags.reconstructions import (
    TAG_RECONSTRUCTIONS_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
    TAG_RECONSTRUCTIONS_BROWSER_GROUP_CONTROLS,
    TAG_RECONSTRUCTIONS_BROWSER_GROUP_TREE,
    TAG_RECONSTRUCTIONS_BROWSER_PANEL,
    TAG_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_RECONSTRUCTIONS_BROWSER_WINDOW_TREE,
)
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.tree.colors import TreeColors
from sampletones_application.ui.elements.tree.protocol import TreeLogicProtocol
from sampletones_application.ui.elements.tree.tags import FileBrowserTags
from sampletones_application.ui.panels.shared.browser import (
    GUIReconstructionBrowserPanel,
)
from sampletones_core.structures.tree import FileSystemNode, Tree
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import PathCallback

_TAGS: Final[FileBrowserTags] = FileBrowserTags(
    panel=TAG_RECONSTRUCTIONS_BROWSER_PANEL,
    tree=TAG_RECONSTRUCTIONS_BROWSER_TREE,
    window_tree=TAG_RECONSTRUCTIONS_BROWSER_WINDOW_TREE,
    group_tree=TAG_RECONSTRUCTIONS_BROWSER_GROUP_TREE,
    group_controls=TAG_RECONSTRUCTIONS_BROWSER_GROUP_CONTROLS,
    button_refresh=TAG_RECONSTRUCTIONS_BROWSER_BUTTON_REFRESH_RECONSTRUCTIONS,
)


class GUIReconstructionsBrowserPanel(GUIReconstructionBrowserPanel):
    """The Reconstructions tab's browser, whose reconstructions open in the tab beside it."""

    def __init__(
        self,
        tree: Tree,
        tree_logic: TreeLogicProtocol,
        *,
        scheduling: SchedulingBehavior,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
        colors: TreeColors,
        initial_collapsed: bool,
    ) -> None:
        self._language_manager = language_manager

        super().__init__(
            tree=tree,
            tree_logic=tree_logic,
            tags=_TAGS,
            scheduling=scheduling,
            language_manager=language_manager,
            status_bar=status_bar,
            colors=colors,
            initial_collapsed=initial_collapsed,
        )

        self.on_load_reconstruction: Optional[PathCallback] = None
        self.on_reconstruction_remove_requested: Optional[PathCallback] = None
        self.on_directory_remove_requested: Optional[PathCallback] = None

    @property
    def refresh_button_label(self) -> str:
        return self._language_manager["reconstructions.browser.label.refresh_button"]

    @property
    def refresh_status_message(self) -> str:
        return self._language_manager["reconstructions.browser.message.status_refresh"]

    def _open_reconstruction(self, node: FileSystemNode) -> None:
        self._load_reconstruction(node)

    def _add_directory_context_menu_items(self, node: FileSystemNode) -> None:
        self._add_context_menu_remove_directory_item(node)

    def _add_reconstruction_context_menu_items(self, node: FileSystemNode) -> None:
        self._add_context_menu_load_reconstruction_item(node)
        self._add_context_menu_remove_reconstruction_item(node)
        self._add_context_menu_sequencer_items(node)

    def _add_context_menu_load_reconstruction_item(
        self,
        node: FileSystemNode,
    ) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["reconstructions.browser.label.context_load_reconstruction"],
            callback=self._on_load_reconstruction,
            user_data=node,
        )

    def _add_context_menu_remove_reconstruction_item(
        self,
        node: FileSystemNode,
    ) -> None:
        dpg.add_menu_item(
            label=self._language_manager["reconstructions.browser.label.context_remove_reconstruction"],
            callback=lambda: self.call(
                self.on_reconstruction_remove_requested,
                node.filepath,
            ),
        )

    def _add_context_menu_remove_directory_item(
        self,
        node: FileSystemNode,
    ) -> None:
        dpg.add_separator()
        dpg.add_menu_item(
            label=self._language_manager["reconstructions.browser.label.context_remove_directory"],
            callback=lambda: self.call(
                self.on_directory_remove_requested,
                node.filepath,
            ),
        )

    def _on_load_reconstruction(
        self,
        _sender: Sender,
        _app_data: Path,
        user_data: FileSystemNode,
    ) -> None:
        self._load_reconstruction(user_data)

    def _load_reconstruction(self, node: FileSystemNode) -> None:
        self._logic.cancel_autoplay()
        self.call(
            self.on_load_reconstruction,
            node.filepath,
        )
