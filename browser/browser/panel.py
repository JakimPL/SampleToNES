from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.browser.manager import BrowserManager
from browser.config.manager import ConfigManager
from browser.panels.tree import GUITreePanel
from browser.tree.node import TreeNode
from constants.browser import (
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BUTTON_REFRESH_LIST,
    LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS,
    NOD_TYPE_FILE,
    TAG_BROWSER_PANEL,
    TAG_BROWSER_TREE,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
)
from constants.general import OUTPUT_DIRECTORY


class GUIBrowserPanel(GUITreePanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        output_directory = config_manager.config.general.output_directory if config_manager.config else OUTPUT_DIRECTORY
        self.browser_manager = BrowserManager(output_directory)
        self._on_reconstruction_selected: Optional[Callable] = None

        super().__init__(
            tag=TAG_BROWSER_PANEL,
            parent_tag=TAG_RECONSTRUCTOR_PANEL_GROUP,
            width=DIM_PANEL_LIBRARY_WIDTH,
            height=DIM_PANEL_LIBRARY_HEIGHT,
        )

        self.tree = self.browser_manager.tree

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, width=self.width, height=self.height, parent=self.parent_tag):
            dpg.add_button(label=LBL_BUTTON_REFRESH_LIST, callback=self._refresh_tree)
            dpg.add_separator()
            with dpg.tree_node(label=LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS, tag=TAG_BROWSER_TREE, default_open=True):
                pass

    def initialize_tree(self) -> None:
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        output_directory = (
            self.config_manager.config.general.output_directory if self.config_manager.config else OUTPUT_DIRECTORY
        )
        self.browser_manager.set_output_directory(output_directory)
        self.build_tree_ui(TAG_BROWSER_TREE)

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        node_type = getattr(user_data, "node_type", None)
        if node_type == NOD_TYPE_FILE and self._on_reconstruction_selected:
            file_path = getattr(user_data, "file_path")
            reconstruction_data = self.browser_manager.load_reconstruction_data(file_path)
            self._on_reconstruction_selected(reconstruction_data)

    def set_callbacks(self, on_reconstruction_selected: Optional[Callable] = None) -> None:
        self._on_reconstruction_selected = on_reconstruction_selected
