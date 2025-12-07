from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.audio import AudioDeviceManager
from sampletones.constants import paths
from sampletones.tree import FileSystemNode, TreeNode
from sampletones.typehints import Color, Sender
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...constants import (
    CHR_STAR,
    COL_PATH_TEXT_HOVER,
    COL_TEXT_DEFAULT,
    COL_TEXT_DISABLED_DEFAULT,
    COL_TEXT_FAVORITE,
    COL_TEXT_LIBRARY,
    COL_TEXT_RECONSTRUCTION,
    COL_TEXT_WAVE,
    LBL_BUTTON_COLLAPSE_ALL,
    LBL_EXPLORER_CONTEXT_ITEM_LOAD_LIBRARY,
    LBL_EXPLORER_CONTEXT_ITEM_LOAD_RECONSTRUCTION,
    LBL_EXPLORER_CONTEXT_ITEM_MARK_AS_FAVORITE,
    LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_DIRECTORY,
    LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_FILE,
    LBL_EXPLORER_CONTEXT_ITEM_SET_AS_LIBRARY_DIRECTORY,
    LBL_EXPLORER_CONTEXT_ITEM_SET_AS_OUTPUT_DIRECTORY,
    LBL_EXPLORER_CONTEXT_ITEM_UNMARK_AS_FAVORITE,
    LBL_EXPLORER_FILESYSTEM,
    LBL_TREE_FILTER,
    MSG_EXPLORER_CONVERTER_RUNNING,
    NOD_TYPE_DIRECTORY,
    NOD_TYPE_FILE,
    NOD_TYPE_ROOT,
    SUF_LEFT_PANEL,
    SUF_NODE_DUMMY,
    SUF_NODE_HANDLER,
    TAG_EXPLORER_COLLAPSE_ALL,
    TAG_EXPLORER_CONVERTER_RUNNING,
    TAG_EXPLORER_PANEL,
    TAG_EXPLORER_TREE,
    TAG_EXPLORER_TREE_GROUP,
    TAG_EXPLORER_TREE_WINDOW,
    TAG_TAB_MAIN,
    TTL_EXPLORER_CONVERTER_RUNNING,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree import GUITreePanel
from ...explorer.manager import ExplorerManager
from ...utils.dialogs import show_info_dialog
from ...utils.dpg import dpg_delete_children, dpg_delete_item

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

        self._on_wave_file_clicked: Optional[OnReconstructPathCallback] = None
        self._on_directory_clicked: Optional[OnReconstructPathCallback] = None
        self._on_reconstruct_directory: Optional[OnReconstructPathCallback] = None
        self._on_reconstruct_file: Optional[OnReconstructPathCallback] = None
        self._on_load_reconstruction: Optional[OnReconstructPathCallback] = None
        self._on_load_library: Optional[OnReconstructPathCallback] = None
        self._on_toggle_mark_as_favorite: Optional[OnReconstructPathCallback] = None
        self._on_set_as_output_directory: Optional[OnReconstructPathCallback] = None
        self._on_set_as_library_directory: Optional[OnReconstructPathCallback] = None
        self._is_converter_running: Optional[Callable[[], bool]] = None

        self._pending_autoplay_node: Optional[FileSystemNode] = None

        super().__init__(
            tree=self.explorer_manager.tree,
            tag=TAG_EXPLORER_PANEL,
            parent=f"{TAG_TAB_MAIN}{SUF_LEFT_PANEL}",
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

        self.initialize_tree()

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

    def _apply_node_theme(self, node_tag: str, node: FileSystemNode) -> None:
        if node.node_type == NOD_TYPE_DIRECTORY:
            return self._apply_directory_node_theme(node_tag, node)

        if node.node_type == NOD_TYPE_FILE:
            return self._apply_file_node_theme(node_tag, node)

        return None

    def _apply_directory_node_theme(self, node_tag: str, node: FileSystemNode) -> None:
        has_content = self.explorer_manager.has_relevant_content(node.filepath)
        is_favorite = node.filepath in self.application_config_manager.favorites

        with dpg.theme() as node_theme:
            with dpg.theme_component(dpg.mvTreeNode):
                if is_favorite:
                    dpg.add_theme_color(dpg.mvThemeCol_Text, COL_TEXT_FAVORITE)
                elif not has_content:
                    dpg.add_theme_color(dpg.mvThemeCol_Text, COL_TEXT_DISABLED_DEFAULT)

        dpg.bind_item_theme(node_tag, node_theme)

    def _apply_file_node_theme(self, node_tag: str, node: FileSystemNode) -> None:
        is_favorite = node.filepath in self.application_config_manager.favorites

        with dpg.theme() as node_theme:
            with dpg.theme_component(dpg.mvSelectable):
                color: Color = COL_TEXT_DEFAULT
                if is_favorite:
                    color = COL_TEXT_FAVORITE
                else:
                    match node.filepath.suffix.lower():
                        case paths.EXT_FILE_RECONSTRUCTION:
                            color = COL_TEXT_RECONSTRUCTION
                        case paths.EXT_FILE_LIBRARY:
                            color = COL_TEXT_LIBRARY
                        case paths.EXT_FILE_WAVE:
                            color = COL_TEXT_WAVE

                dpg.add_theme_color(dpg.mvThemeCol_Text, color)

        dpg.bind_item_theme(node_tag, node_theme)

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
                self._apply_node_theme(node_tag, node)

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

            self._apply_node_theme(node_tag, node)
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
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            match user_data.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    return self._load_reconstruction(user_data)
                case paths.EXT_FILE_LIBRARY:
                    return self._load_library(user_data)
                case paths.EXT_FILE_WAVE:

                    if self._on_wave_file_clicked is not None:
                        self._on_wave_file_clicked(user_data.filepath)
                    return self._schedule_autoplay(user_data)
                case _:
                    logger.warning(f"Unhandled file type clicked: {user_data.filepath.suffix.lower()}")
                    return None

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_file_context_menu(user_data)

        return None

    def _on_file_node_double_clicked(
        self, sender: Sender, app_data: Tuple[int, int], user_data: FileSystemNode
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            self._pending_autoplay_node = None
            return self._reconstruct_file(user_data)

        return None

    def _on_directory_node_clicked(self, sender: Sender, app_data: Tuple[int, int], user_data: FileSystemNode) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            return self._directory_node_clicked(user_data)

        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(user_data)

        return None

    def _directory_node_clicked(self, node: FileSystemNode) -> None:
        self._toggle_directory_expansion(node)
        has_content = self.explorer_manager.has_relevant_content(node.filepath)
        if not has_content:
            return

        if self._on_directory_clicked is not None:
            self._on_directory_clicked(node.filepath)

    def _load_reconstruction(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if self._on_load_reconstruction is not None and filepath.exists():
            self._set_explorer_tree_enabled(False)
            try:
                self._on_load_reconstruction(filepath)
            finally:
                self._set_explorer_tree_enabled(True)

    def _load_library(self, node: FileSystemNode) -> None:
        filepath = node.filepath
        if self._on_load_library is not None and filepath.exists():
            self._set_explorer_tree_enabled(False)
            try:
                self._on_load_library(filepath)
            finally:
                self._set_explorer_tree_enabled(True)

    def _schedule_autoplay(self, node: FileSystemNode) -> None:
        self._pending_autoplay_node = node
        dpg.set_frame_callback(dpg.get_frame_count() + 12, self._execute_autoplay)

    def _autoplay_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        if self.application_config_manager.autoplay:
            self.audio_device_manager.play_file(node.filepath)

    def _execute_autoplay(self) -> None:
        if self._pending_autoplay_node is not None:
            self._autoplay_file(self._pending_autoplay_node)
            self._pending_autoplay_node = None

    def _reconstruct_file(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        if self._check_if_converter_running():
            return

        if self._on_reconstruct_file is not None:
            self._on_reconstruct_file(node.filepath)

    def _toggle_directory_expansion(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_DIRECTORY:
            return

        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        is_currently_expanded = self.explorer_manager.is_directory_expanded(node.filepath)
        is_currently_expanded &= dpg.get_item_configuration(node_tag).get("open", False)

        if is_currently_expanded:
            self.explorer_manager.collapse_directory(node.filepath)
            self.explorer_manager.clear_directory_children(node)
        else:
            self.explorer_manager.expand_directory(node)

        self._rebuild_node_subtree(node)

    def _rebuild_node_subtree(self, node: FileSystemNode) -> None:
        node_tag = self._generate_node_tag(node)
        if not dpg.does_item_exist(node_tag):
            return

        dpg_delete_children(node_tag)
        if self.explorer_manager.is_directory_expanded(node.filepath):
            for child in node.children:
                self._build_tree_node(child, node_tag)
        else:
            dummy_tag = f"{node_tag}{SUF_NODE_DUMMY}"
            dpg.add_tree_node(
                label="",
                tag=dummy_tag,
                parent=node_tag,
                leaf=True,
            )

    def _add_context_menu_text(self, node: FileSystemNode) -> None:
        is_favorite = node.filepath in self.application_config_manager.favorites
        color = COL_TEXT_FAVORITE if is_favorite else COL_PATH_TEXT_HOVER

        with dpg.group(horizontal=True):
            if is_favorite:
                star = chr(CHR_STAR)
                star_text = dpg.add_text(star, color=color)
                FontRegistry.bind_to_item(star_text, Font.ICON)

            text = dpg.add_text(node.name, color=color)
            FontRegistry.bind_to_item(text, Font.BOLD)

    def _add_context_menu_favorite_item(self, node: FileSystemNode) -> None:
        label = (
            LBL_EXPLORER_CONTEXT_ITEM_UNMARK_AS_FAVORITE
            if node.filepath in self.application_config_manager.favorites
            else LBL_EXPLORER_CONTEXT_ITEM_MARK_AS_FAVORITE
        )
        dpg.add_menu_item(
            label=label,
            callback=lambda: self._context_mark_as_favorite(node),
        )

    def _show_file_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NOD_TYPE_FILE:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            modal=False,
        ):
            self._add_context_menu_text(node)
            dpg.add_separator()
            match node.filepath.suffix.lower():
                case paths.EXT_FILE_RECONSTRUCTION:
                    dpg.add_menu_item(
                        label=LBL_EXPLORER_CONTEXT_ITEM_LOAD_RECONSTRUCTION,
                        callback=lambda: self._load_reconstruction(node),
                    )
                case paths.EXT_FILE_LIBRARY:
                    dpg.add_menu_item(
                        label=LBL_EXPLORER_CONTEXT_ITEM_LOAD_LIBRARY,
                        callback=lambda: self._load_library(node),
                    )
                case paths.EXT_FILE_WAVE:
                    dpg.add_menu_item(
                        label=LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_FILE,
                        callback=lambda: self._context_reconstruct_file(node),
                    )

            self._add_context_menu_favorite_item(node)

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
            self._add_context_menu_text(node)
            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_RECONSTRUCT_DIRECTORY,
                callback=lambda: self._context_reconstruct_directory(node),
            )

            self._add_context_menu_favorite_item(node)
            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_SET_AS_OUTPUT_DIRECTORY,
                callback=lambda: self._context_set_as_output_directory(node),
            )

            dpg.add_menu_item(
                label=LBL_EXPLORER_CONTEXT_ITEM_SET_AS_LIBRARY_DIRECTORY,
                callback=lambda: self._context_set_as_library_directory(node),
            )

    def _check_if_converter_running(self) -> bool:
        if self._is_converter_running is not None:
            if self._is_converter_running():
                logger.warning("Conversion is already running. Wait or cancel the current operation.")
                show_info_dialog(
                    tag=TAG_EXPLORER_CONVERTER_RUNNING,
                    message=MSG_EXPLORER_CONVERTER_RUNNING,
                    title=TTL_EXPLORER_CONVERTER_RUNNING,
                )
                return True

        return False

    def _context_reconstruct_file(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        if self._on_reconstruct_file is not None:
            self._on_reconstruct_file(node.filepath)

    def _context_reconstruct_directory(self, node: FileSystemNode) -> None:
        if self._check_if_converter_running():
            return

        if self._on_reconstruct_directory is not None:
            self._on_reconstruct_directory(node.filepath)

    def _context_mark_as_favorite(self, node: FileSystemNode) -> None:
        if self._on_toggle_mark_as_favorite is not None:
            self._on_toggle_mark_as_favorite(node.filepath)

        self.application_config_manager.toggle_favorite(node.filepath)
        self._update_favorite_indicator(node)

    def _context_set_as_output_directory(self, node: FileSystemNode) -> None:
        if self._on_set_as_output_directory is not None:
            self._on_set_as_output_directory(node.filepath)

    def _context_set_as_library_directory(self, node: FileSystemNode) -> None:
        if self._on_set_as_library_directory is not None:
            self._on_set_as_library_directory(node.filepath)

    def _update_favorite_indicator(self, node: FileSystemNode) -> None:
        node_tag = self._generate_node_tag(node)
        if dpg.does_item_exist(node_tag):
            self._apply_node_theme(node_tag, node)

    def set_callbacks(
        self,
        on_wave_file_clicked: Optional[OnReconstructPathCallback] = None,
        on_directory_clicked: Optional[OnReconstructPathCallback] = None,
        on_reconstruct_directory: Optional[OnReconstructPathCallback] = None,
        on_reconstruct_file: Optional[OnReconstructPathCallback] = None,
        on_load_reconstruction: Optional[OnReconstructPathCallback] = None,
        on_load_library: Optional[OnReconstructPathCallback] = None,
        on_toggle_mark_as_favorite: Optional[OnReconstructPathCallback] = None,
        on_set_as_output_directory: Optional[OnReconstructPathCallback] = None,
        on_set_as_library_directory: Optional[OnReconstructPathCallback] = None,
        is_converter_running: Optional[Callable[[], bool]] = None,
    ) -> None:
        if on_wave_file_clicked is not None:
            self._on_wave_file_clicked = on_wave_file_clicked
        if on_directory_clicked is not None:
            self._on_directory_clicked = on_directory_clicked
        if on_reconstruct_directory is not None:
            self._on_reconstruct_directory = on_reconstruct_directory
        if on_reconstruct_file is not None:
            self._on_reconstruct_file = on_reconstruct_file
        if on_load_reconstruction is not None:
            self._on_load_reconstruction = on_load_reconstruction
        if on_load_library is not None:
            self._on_load_library = on_load_library
        if on_toggle_mark_as_favorite is not None:
            self._on_toggle_mark_as_favorite = on_toggle_mark_as_favorite
        if on_set_as_output_directory is not None:
            self._on_set_as_output_directory = on_set_as_output_directory
        if on_set_as_library_directory is not None:
            self._on_set_as_library_directory = on_set_as_library_directory
        if is_converter_running is not None:
            self._is_converter_running = is_converter_running
