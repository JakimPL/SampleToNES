from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager
from sampletones.tree import FileSystemNode, TreeNode
from sampletones.typehints import Sender

from ...config.application.manager import ApplicationConfigManager
from ...constants import (
    COL_PATH_TEXT_HOVER,
    DIM_PANEL_EXPLORER_HEIGHT,
    DIM_PANEL_EXPLORER_WIDTH,
    LBL_BUTTON_COLLAPSE_ALL,
    LBL_EXPLORER_CONTEXT_ITEM_MARK_AS_FAVORITE,
    LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_DIRECTORY,
    LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_FILE,
    LBL_EXPLORER_FILESYSTEM,
    LBL_TREE_FILTER,
    NOD_TYPE_DIRECTORY,
    NOD_TYPE_FILE,
    NOD_TYPE_ROOT,
    SUF_NODE_DUMMY,
    SUF_NODE_HANDLER,
    TAG_EXPLORER_COLLAPSE_ALL,
    TAG_EXPLORER_PANEL,
    TAG_EXPLORER_PANEL_GROUP,
    TAG_EXPLORER_TREE,
    TAG_EXPLORER_TREE_GROUP,
    TAG_EXPLORER_TREE_WINDOW,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree import GUITreePanel
from ...explorer.manager import ExplorerManager
from ...utils.dpg import dpg_delete_item

OnReconstructPathCallback = Callable[[Path], None]


class GUIExplorerPanel(GUITreePanel):
    def __init__(
        self,
        audio_device_manager: AudioDeviceManager,
        application_config_manager: ApplicationConfigManager,
    ) -> None:
        self.explorer_manager = ExplorerManager()
        self.audio_device_manager = audio_device_manager
        self.application_config_manager = application_config_manager

        self._on_reconstruct_directory: Optional[OnReconstructPathCallback] = None
        self._on_reconstruct_file: Optional[OnReconstructPathCallback] = None
        self._on_toggle_mark_as_favorite: Optional[OnReconstructPathCallback] = None

        super().__init__(
            tree=self.explorer_manager.tree,
            tag=TAG_EXPLORER_PANEL,
            parent=TAG_EXPLORER_PANEL_GROUP,
            width=DIM_PANEL_EXPLORER_WIDTH,
            height=DIM_PANEL_EXPLORER_HEIGHT,
            search_label=LBL_TREE_FILTER,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
        ):
            self._create_section_text()
            self._create_collapse_button()
            self._create_tree_window()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_EXPLORER_FILESYSTEM)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_collapse_button(self) -> None:
        dpg.add_separator()
        GUIButton(
            tag=TAG_EXPLORER_COLLAPSE_ALL,
            label=LBL_BUTTON_COLLAPSE_ALL,
            parent=self.tag,
            width=-1,
            callback=self.collapse_all,
        )

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_EXPLORER_TREE_WINDOW):
            with dpg.group(tag=TAG_EXPLORER_TREE_GROUP):
                with dpg.tree_node(label=LBL_EXPLORER_FILESYSTEM, tag=TAG_EXPLORER_TREE, default_open=True):
                    pass

    def collapse_all(self, sender: Sender, app_data: int, user_data: object) -> None:
        self.explorer_manager.collapse_all()
        self._rebuild_tree()

    def initialize_tree(self) -> None:
        self._refresh_tree()

    def refresh(self) -> None:
        self._refresh_tree()

    def _rebuild_tree(self) -> None:
        self.build_tree(TAG_EXPLORER_TREE)

    def _refresh_tree(self) -> None:
        self._set_explorer_tree_enabled(False)
        try:
            self.explorer_manager.refresh_tree()
            self._rebuild_tree()
        finally:
            self._set_explorer_tree_enabled(True)

    def _set_explorer_tree_enabled(self, enabled: bool) -> None:
        dpg.configure_item(TAG_EXPLORER_TREE_GROUP, enabled=enabled)

    def _build_tree_node(self, node: TreeNode, parent: str) -> None:
        node_tag = self._generate_node_tag(node)

        if node.node_type == NOD_TYPE_ROOT:
            return

        if not isinstance(node, FileSystemNode):
            return

        handler_registry_tag = f"{node_tag}{SUF_NODE_HANDLER}"
        if node.node_type == NOD_TYPE_DIRECTORY:
            should_expand = self._should_expand_node(node) or self.explorer_manager.is_directory_expanded(node.filepath)
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=parent,
                default_open=should_expand,
                open_on_arrow=False,
            ) as tree_node_tag:
                FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)

                if self.explorer_manager.is_directory_expanded(node.filepath):
                    for child in node.children:
                        self._build_tree_node(child, node_tag)

                dpg.add_tree_node(
                    label="",
                    tag=f"{node_tag}{SUF_NODE_DUMMY}",
                    parent=tree_node_tag,
                    show=not self.explorer_manager.is_directory_expanded(node.filepath),
                )

            self._add_item_handler_registry(
                tag=handler_registry_tag,
                parent=node_tag,
                item_click_callback=self._on_directory_node_clicked,
                item_double_click_callback=None,
                node=node,
            )
        else:
            dpg.add_selectable(
                label=node.name,
                parent=parent,
                callback=self._on_selectable_clicked,
                user_data=node,
                tag=node_tag,
                default_value=False,
            )
            FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)

            self._add_item_handler_registry(
                tag=handler_registry_tag,
                parent=node_tag,
                item_click_callback=self._on_file_node_clicked,
                item_double_click_callback=self._on_file_node_double_clicked,
                node=node,
            )

    def _add_item_handler_registry(
        self,
        tag: str,
        parent: str,
        item_click_callback: Callable[[Sender, Tuple[int, int], Any], None],
        item_double_click_callback: Optional[Callable[[Sender, Tuple[int, int], Any], None]],
        node: TreeNode,
    ) -> None:
        dpg_delete_item(tag)
        with dpg.item_handler_registry(tag=tag):
            if item_click_callback is not None:
                dpg.add_item_clicked_handler(
                    callback=item_click_callback,
                    user_data=node,
                )
            if item_double_click_callback is not None:
                dpg.add_item_double_clicked_handler(
                    callback=item_double_click_callback,
                    user_data=node,
                )

        dpg.bind_item_handler_registry(parent, tag)

    def _on_file_node_clicked(self, sender: Sender, app_data: Tuple[int, int], user_data: FileSystemNode) -> None:
        mouse_button, click_count = app_data
        if mouse_button == dpg.mvMouseButton_Left and click_count == 1:
            return self._autoplay_file(user_data)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_file_context_menu(user_data)

        return None

    def _on_file_node_double_clicked(
        self, sender: Sender, app_data: Tuple[int, int], user_data: FileSystemNode
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            return self._reconstruct_file(user_data)

        return None

    def _on_directory_node_clicked(self, sender: Sender, app_data: Tuple[int, int], user_data: FileSystemNode) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            return self._toggle_directory_expansion(user_data)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(user_data)

        return None

    def _autoplay_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        if self.application_config_manager.autoplay:
            self.audio_device_manager.play_file(node.filepath)

    def _reconstruct_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        if self._on_reconstruct_file is not None:
            self._on_reconstruct_file(node.filepath)

    def _toggle_directory_expansion(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_DIRECTORY:
            return

        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        self._set_explorer_tree_enabled(False)
        try:
            is_currently_expanded = self.explorer_manager.is_directory_expanded(node.filepath)

            if is_currently_expanded:
                self.explorer_manager.collapse_directory(node.filepath)
                self.explorer_manager.clear_directory_children(node)
            else:
                self.explorer_manager.expand_directory(node)

            self._rebuild_tree()
        finally:
            self._set_explorer_tree_enabled(True)

    def _show_file_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        with dpg.window(popup=True, no_move=True, no_resize=True, no_title_bar=True, modal=False):
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_FILE,
                callback=lambda: self._context_reconstruct_file(node),
            )
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_MARK_AS_FAVORITE,
                callback=lambda: self._context_mark_as_favorite(node),
            )

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_DIRECTORY:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            modal=False,
        ):
            text = dpg.add_text(node.name, color=COL_PATH_TEXT_HOVER)
            FontRegistry.bind_to_item(text, Font.BOLD)

            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_DIRECTORY,
                callback=lambda: self._context_reconstruct_directory(node),
            )
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_MARK_AS_FAVORITE,
                callback=lambda: self._context_mark_as_favorite(node),
            )

    def _context_reconstruct_file(self, node: FileSystemNode) -> None:
        if self._on_reconstruct_file is not None:
            self._on_reconstruct_file(node.filepath)

    def _context_reconstruct_directory(self, node: FileSystemNode) -> None:
        if self._on_reconstruct_directory is not None:
            self._on_reconstruct_directory(node.filepath)

    def _context_mark_as_favorite(self, node: FileSystemNode) -> None:
        if self._on_toggle_mark_as_favorite is not None:
            self._on_toggle_mark_as_favorite(node.filepath)

    def set_callbacks(
        self,
        on_reconstruct_directory: Optional[OnReconstructPathCallback] = None,
        on_reconstruct_file: Optional[OnReconstructPathCallback] = None,
        on_toggle_mark_as_favorite: Optional[OnReconstructPathCallback] = None,
    ) -> None:
        if on_reconstruct_directory is not None:
            self._on_reconstruct_directory = on_reconstruct_directory
        if on_reconstruct_file is not None:
            self._on_reconstruct_file = on_reconstruct_file
        if on_toggle_mark_as_favorite is not None:
            self._on_toggle_mark_as_favorite = on_toggle_mark_as_favorite
