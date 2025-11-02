from pathlib import Path

import dearpygui.dearpygui as dpg

from browser.browser.manager import BrowserManager, ReconstructionNode
from browser.config.manager import ConfigManager
from browser.panel import GUIPanel
from constants.browser import (
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BUTTON_REFRESH_LIST,
    LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS,
    TAG_BROWSER_PANEL,
    TAG_BROWSER_TREE,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
    VAL_GLOBAL_DEFAULT_SLOT,
)
from constants.general import OUTPUT_DIRECTORY


class GUIBrowserPanel(GUIPanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        output_directory = config_manager.config.general.output_directory if config_manager.config else OUTPUT_DIRECTORY
        self.browser_manager = BrowserManager(output_directory)

        super().__init__(
            tag=TAG_BROWSER_PANEL,
            parent_tag=TAG_RECONSTRUCTOR_PANEL_GROUP,
            width=DIM_PANEL_LIBRARY_WIDTH,
            height=DIM_PANEL_LIBRARY_HEIGHT,
        )

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
        self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        self._clear_children(TAG_BROWSER_TREE)

        tree = self.browser_manager.get_tree()
        if tree is None:
            return

        for child in tree.children:
            self._build_tree_node(child, TAG_BROWSER_TREE)

    def _build_tree_node(self, node: ReconstructionNode, parent_tag: str) -> None:
        node_tag = self._generate_node_tag(node.path)

        if node.is_file:
            dpg.add_selectable(label=node.name, parent=parent_tag, callback=self._on_file_selected, user_data=node.path)
        else:
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent_tag):
                for child in node.children:
                    self._build_tree_node(child, node_tag)

    def _generate_node_tag(self, path: Path) -> str:
        return f"browser_node_{str(path).replace('/', '_').replace('.', '_')}"

    def _on_file_selected(self, sender: int, app_data: bool, user_data: Path) -> None:
        pass

    def _clear_children(self, tag: str) -> None:
        children = dpg.get_item_children(tag, slot=VAL_GLOBAL_DEFAULT_SLOT) or []
        for child in children:
            dpg.delete_item(child)
