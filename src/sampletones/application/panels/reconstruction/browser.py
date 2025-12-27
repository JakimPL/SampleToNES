from pathlib import Path
from typing import Any, Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.exceptions import (
    IncompatibleReconstructionVersionError,
    InvalidMetadataError,
    InvalidReconstructionError,
    InvalidReconstructionValuesError,
)
from sampletones.tree import FileSystemNode, NodeType, TreeNode
from sampletones.typehints import Sender, VoidCallback
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import (
    MSG_GLOBAL_INVALID_METADATA_ERROR,
    SUF_PANEL_LEFT,
    TAG_TAB_RECONSTRUCTIONS,
)
from ...constants.reconstructions import (
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_LIST,
    LBL_CONTEXT_ITEM_RECONSTRUCTIONS_BROWSER_LOAD_RECONSTRUCTION,
    LBL_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS,
    LBL_TREE_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS,
    MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE,
    MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES,
    MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_RECONSTRUCTIONS,
    TAG_GROUP_RECONSTRUCTIONS_BROWSER_CONTROLS,
    TAG_GROUP_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_PANEL_RECONSTRUCTIONS_BROWSER,
    TAG_TREE_RECONSTRUCTIONS_BROWSER,
    TAG_WINDOW_RECONSTRUCTIONS_BROWSER_TREE,
    TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree.tree import GUITreePanel
from ...reconstruction.browser import BrowserManager
from ...reconstruction.data import ReconstructionData
from ...reconstruction.manager import ReconstructionManager
from ...utils.dialogs import show_error_dialog, show_file_not_found_dialog
from ...utils.dpg import dpg_configure_item
from ...utils.thread import concurrent

OnLoadReconstructionCallback = Callable[[Path], None]
OnReconstructionLoadedCallback = Callable[[ReconstructionData], None]


class GUIBrowserPanel(GUITreePanel):
    def __init__(
        self,
        config_manager: ConfigManager,
        application_config_manager: ApplicationConfigManager,
        browser_manager: BrowserManager,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        self.config_manager = config_manager
        self.application_config_manager = application_config_manager
        self.browser_manager = browser_manager
        self.reconstruction_manager = reconstruction_manager

        self._building_tree: bool = False
        self._loading_reconstruction: bool = False

        self.on_load_reconstruction: Optional[OnLoadReconstructionCallback] = None
        self.on_reconstruction_loaded: Optional[OnReconstructionLoadedCallback] = None
        self.on_reconstruct_file: Optional[VoidCallback] = None
        self.on_reconstruct_directory: Optional[VoidCallback] = None

        super().__init__(
            tree=self.browser_manager.tree,
            tag=TAG_PANEL_RECONSTRUCTIONS_BROWSER,
            parent=f"{TAG_TAB_RECONSTRUCTIONS}{SUF_PANEL_LEFT}",
            tree_tag=TAG_TREE_RECONSTRUCTIONS_BROWSER,
            application_config_manager=application_config_manager,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
            border=False,
        ):
            self._create_section_text()
            self._create_buttons()
            self._create_tree_window()

        self._rebuild_tree()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_buttons(self) -> None:
        dpg.add_separator()
        with dpg.group(tag=TAG_GROUP_RECONSTRUCTIONS_BROWSER_CONTROLS):
            GUIButton(
                tag=TAG_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_RECONSTRUCTIONS,
                label=LBL_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_LIST,
                width=-1,
                callback=self._rebuild_tree,
            )
            GUIButton(
                tag=TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
                label=LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
                width=-1,
                callback=self._reconstruct_file,
                font=Font.BOLD,
            )
            GUIButton(
                tag=TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
                label=LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
                width=-1,
                callback=self._reconstruct_directory,
                font=Font.BOLD,
            )

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_WINDOW_RECONSTRUCTIONS_BROWSER_TREE):
            with dpg.group(tag=TAG_GROUP_RECONSTRUCTIONS_BROWSER_TREE):
                with dpg.tree_node(
                    label=LBL_TREE_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS,
                    tag=self.tree_tag,
                    default_open=True,
                ):
                    pass

    def refresh(self) -> None:
        self._rebuild_tree()

    @concurrent(wait=False, method_bound=True)
    def _rebuild_tree(self) -> None:
        if self._building_tree:
            return

        self._building_tree = True
        try:
            self._delete_item_handler_registries()
            output_directory = self.config_manager.get_output_directory()
            self.browser_manager.set_output_directory(output_directory)
            self.build_tree()
        except SystemError:
            logger.warning("Application failed during rebuilding the reconstructions browser tree")
        finally:
            self._building_tree = False
            self._assign_item_handler_registries()

    def _has_relevant_content(self, node: TreeNode) -> bool:
        if node.node_type == NodeType.FILE:
            return True

        return bool(node.children)

    def _build_tree_node(
        self,
        node: TreeNode,
        parent: str,
        has_favorite_ancestor: bool = False,
        **kwargs: Any,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        self._handlers.clear()
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, FileSystemNode):
            return

        is_favorite = node.node_type != NodeType.ROOT and self._is_node_favorite(node)
        has_favorite_ancestor |= is_favorite
        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node)
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=parent,
                default_open=should_expand,
            ):
                self._apply_node_theme(
                    node_tag,
                    node,
                    has_favorite_ancestor=has_favorite_ancestor,
                )
                for child in node.children:
                    self._build_tree_node(child, node_tag, has_favorite_ancestor)

            self._add_item_handler_registry(
                node_tag=node_tag,
                node=node,
                item_click_callback=self._on_directory_node_clicked,
            )
        else:
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=parent,
                leaf=True,
            ):
                self._apply_node_theme(
                    node_tag,
                    node,
                    has_favorite_ancestor=has_favorite_ancestor,
                )

            self._add_item_handler_registry(
                node_tag=node_tag,
                node=node,
                item_click_callback=self._on_reconstruction_node_clicked,
            )

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_RECONSTRUCTIONS_BROWSER_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_RECONSTRUCTIONS_BROWSER_CONTROLS, enabled=enabled)

    def _on_selectable_clicked(self, sender: Sender, app_data: bool, user_data: TreeNode) -> None:
        super()._on_selectable_clicked(sender, app_data, user_data)

        if isinstance(user_data, FileSystemNode):
            self.call(self.on_load_reconstruction, user_data.filepath)

    def _reconstruct_file(self) -> None:
        self.call(self.on_reconstruct_file)

    def _reconstruct_directory(self) -> None:
        self.call(self.on_reconstruct_directory)

    def _on_directory_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: FileSystemNode,
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(user_data)

        return None

    def _on_reconstruction_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: FileSystemNode,
    ) -> None:
        mouse_button, _ = app_data
        if mouse_button == dpg.mvMouseButton_Left:
            self.load_reconstruction(user_data.filepath)

        if mouse_button == dpg.mvMouseButton_Right:
            self._show_reconstruction_context_menu(user_data)

    def _show_directory_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.DIRECTORY:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            min_size=(0, 0),
            modal=False,
        ):
            self._add_context_menu_text(node)
            dpg.add_separator()
            self._add_context_menu_favorite_item(node)

    def _show_reconstruction_context_menu(self, node: FileSystemNode) -> None:
        if not isinstance(node, FileSystemNode) or node.node_type != NodeType.FILE:
            return

        with dpg.window(
            popup=True,
            no_move=True,
            no_resize=True,
            no_title_bar=True,
            min_size=(0, 0),
            modal=False,
        ):
            self._add_context_menu_text(node)
            dpg.add_separator()
            dpg.add_menu_item(
                label=LBL_CONTEXT_ITEM_RECONSTRUCTIONS_BROWSER_LOAD_RECONSTRUCTION,
                callback=self._on_load_reconstruction,
                user_data=node,
            )
            dpg.add_separator()
            self._add_context_menu_favorite_item(node)

    def _on_load_reconstruction(self, sender: Sender, app_data: Path, user_data: FileSystemNode) -> None:
        self.call(self.on_load_reconstruction, user_data.filepath)

    @concurrent(wait=True, method_bound=True)
    def load_reconstruction(self, filepath: Path) -> None:
        if self._loading_reconstruction:
            return None

        self._set_tree_enabled(False)
        self._loading_reconstruction = True
        try:
            self.reconstruction_manager.load_reconstruction(filepath)
        except FileNotFoundError as exception:
            logger.error_with_traceback(exception, f"Failed to load reconstruction data from {filepath}")
            return show_file_not_found_dialog(filepath, MSG_RECONSTRUCTIONS_BROWSER_RECONSTRUCTION_FILE_NOT_FOUND)
        except (IOError, IsADirectoryError, PermissionError, OSError) as exception:
            logger.error_with_traceback(exception, f"Error while loading reconstruction data from {filepath}")
            return show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        except InvalidMetadataError as exception:
            logger.error_with_traceback(exception, f"Invalid metadata in the reconstruction file {filepath}")
            return show_error_dialog(exception, MSG_GLOBAL_INVALID_METADATA_ERROR)
        except InvalidReconstructionValuesError as exception:
            logger.error_with_traceback(exception, f"Reconstruction contains invalid values: {filepath}")
            return show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_VALUES)
        except InvalidReconstructionError as exception:
            logger.error_with_traceback(exception, f"Invalid reconstruction file: {filepath}")
            return show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_INVALID_RECONSTRUCTION_FILE)
        except IncompatibleReconstructionVersionError as exception:
            logger.error_with_traceback(
                exception,
                f"Incompatible reconstruction version: {exception.actual_version}"
                f" != expected {exception.expected_version}",
            )
            return show_error_dialog(
                exception,
                TPL_RECONSTRUCTIONS_BROWSER_INCOMPATIBLE_RECONSTRUCTION_FILE.format(
                    exception.actual_version,
                    exception.expected_version,
                ),
            )
        except Exception as exception:
            logger.error_with_traceback(
                exception, f"Unexpected error while loading reconstruction data from {filepath}"
            )
            return show_error_dialog(exception, MSG_RECONSTRUCTIONS_BROWSER_FILE_LOAD_ERROR)
        finally:
            self._loading_reconstruction = False
            self._set_tree_enabled(True)

        logger.info(f"Loaded reconstruction: {logger.format_path(filepath)}")
        return self.application_config_manager.set_current_reconstruction(filepath)
