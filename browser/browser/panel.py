from pathlib import Path
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from browser.browser.manager import BrowserManager
from browser.config.manager import ConfigManager
from browser.elements.tree import GUITreePanel
from browser.tree.node import FileSystemNode, TreeNode
from browser.utils import show_error_dialog, show_file_not_found_dialog
from constants.browser import (
    DIM_PANEL_LIBRARY_HEIGHT,
    DIM_PANEL_LIBRARY_WIDTH,
    LBL_BROWSER_RECONSTRUCTIONS,
    LBL_BUTTON_RECONSTRUCT_DIRECTORY,
    LBL_BUTTON_RECONSTRUCT_FILE,
    LBL_BUTTON_REFRESH_LIST,
    LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS,
    MSG_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND,
    MSG_RECONSTRUCTION_FILE_NOT_FOUND,
    NOD_TYPE_DIRECTORY,
    TAG_BROWSER_BUTTON_RECONSTRUCT_DIRECTORY,
    TAG_BROWSER_BUTTON_RECONSTRUCT_FILE,
    TAG_BROWSER_CONTROLS_GROUP,
    TAG_BROWSER_PANEL,
    TAG_BROWSER_TREE,
    TAG_BROWSER_TREE_GROUP,
    TAG_RECONSTRUCTOR_PANEL_GROUP,
)
from exceptions.reconstruction import InvalidReconstructionError
from utils.logger import logger


class GUIBrowserPanel(GUITreePanel):
    def __init__(self, config_manager: ConfigManager) -> None:
        self.config_manager = config_manager
        output_directory = config_manager.get_output_directory()
        self.browser_manager = BrowserManager(output_directory)

        self._on_reconstruction_selected: Optional[Callable] = None
        self._on_reconstruct_file: Optional[Callable] = None
        self._on_reconstruct_directory: Optional[Callable] = None

        super().__init__(
            tree=self.browser_manager.tree,
            tag=TAG_BROWSER_PANEL,
            parent=TAG_RECONSTRUCTOR_PANEL_GROUP,
            width=DIM_PANEL_LIBRARY_WIDTH,
            height=DIM_PANEL_LIBRARY_HEIGHT,
        )

    def create_panel(self) -> None:
        with dpg.child_window(tag=self.tag, width=self.width, height=self.height, parent=self.parent):
            dpg.add_text(LBL_BROWSER_RECONSTRUCTIONS)
            dpg.add_separator()
            with dpg.group(tag=TAG_BROWSER_CONTROLS_GROUP):
                dpg.add_button(
                    label=LBL_BUTTON_REFRESH_LIST,
                    width=-1,
                    callback=self._refresh_tree,
                )
                dpg.add_button(
                    label=LBL_BUTTON_RECONSTRUCT_FILE,
                    width=-1,
                    callback=self._reconstruct_file,
                    tag=TAG_BROWSER_BUTTON_RECONSTRUCT_FILE,
                )
                dpg.add_button(
                    label=LBL_BUTTON_RECONSTRUCT_DIRECTORY,
                    width=-1,
                    callback=self._reconstruct_directory,
                    tag=TAG_BROWSER_BUTTON_RECONSTRUCT_DIRECTORY,
                )

            dpg.add_separator()
            self.create_search(self.tag)
            dpg.add_separator()
            with dpg.group(tag=TAG_BROWSER_TREE_GROUP):
                with dpg.tree_node(label=LBL_OUTPUT_AVAILABLE_RECONSTRUCTIONS, tag=TAG_BROWSER_TREE, default_open=True):
                    pass

    def refresh(self) -> None:
        self._refresh_tree()

    def _rebuild_tree(self) -> None:
        self.build_tree(TAG_BROWSER_TREE)

    def _build_tree_node(self, node: TreeNode, parent: str) -> None:
        node_tag = self._generate_node_tag(node)

        if isinstance(node, FileSystemNode) and node.node_type == NOD_TYPE_DIRECTORY:
            should_expand = self._should_expand_node(node)
            with dpg.tree_node(label=node.name, tag=node_tag, parent=parent, default_open=should_expand):
                for child in node.children:
                    self._build_tree_node(child, node_tag)
        else:
            dpg.add_selectable(
                label=node.name,
                parent=parent,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )

    def initialize_tree(self) -> None:
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        dpg.configure_item(TAG_BROWSER_TREE_GROUP, enabled=False)
        output_directory = self.config_manager.get_output_directory()
        self.browser_manager.set_output_directory(output_directory)
        self._rebuild_tree()
        dpg.configure_item(TAG_BROWSER_TREE_GROUP, enabled=True)

    def _on_selectable_clicked(self, sender: int, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if isinstance(user_data, FileSystemNode):
            self.load_and_display_reconstruction(user_data.filepath)

    def _reconstruct_file(self) -> None:
        if self._on_reconstruct_file is not None:
            self._on_reconstruct_file()

    def _reconstruct_directory(self) -> None:
        if self._on_reconstruct_directory is not None:
            self._on_reconstruct_directory()

    def load_and_display_reconstruction(self, filepath: Path) -> None:
        try:
            reconstruction_data = self.browser_manager.load_reconstruction_data(filepath)
        except FileNotFoundError as error:
            missing_file = Path(error.filename)
            logger.error_with_traceback(f"Failed to load reconstruction data from {filepath}", error)
            if missing_file == filepath:
                show_file_not_found_dialog(filepath, MSG_RECONSTRUCTION_FILE_NOT_FOUND)
            else:
                show_file_not_found_dialog(missing_file, MSG_RECONSTRUCTION_AUDIO_FILE_NOT_FOUND)
            return
        except (IsADirectoryError, OSError, PermissionError) as exception:
            logger.error_with_traceback(f"Error while loading reconstruction data from {filepath}", exception)
            show_error_dialog(exception)
            return
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(f"Invalid reconstruction file: {filepath}", exception)
            show_error_dialog(exception)
            return

        if self._on_reconstruction_selected:
            dpg.configure_item(TAG_BROWSER_TREE_GROUP, enabled=False)
            self._on_reconstruction_selected(reconstruction_data)
            dpg.configure_item(TAG_BROWSER_TREE_GROUP, enabled=True)

    def set_callbacks(
        self,
        on_reconstruction_selected: Optional[Callable] = None,
        on_reconstruct_file: Optional[Callable] = None,
        on_reconstruct_directory: Optional[Callable] = None,
    ) -> None:
        if on_reconstruction_selected is not None:
            self._on_reconstruction_selected = on_reconstruction_selected
        if on_reconstruct_file is not None:
            self._on_reconstruct_file = on_reconstruct_file
        if on_reconstruct_directory is not None:
            self._on_reconstruct_directory = on_reconstruct_directory
