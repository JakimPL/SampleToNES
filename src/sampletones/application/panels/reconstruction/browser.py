from pathlib import Path
from typing import Callable, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones.tree import FileSystemNode, NodeType, TreeNode, TreeTraversal, traverse
from sampletones.typehints import Sender, VoidCallback
from sampletones.utils.logger import logger

from ...config.application.manager import ApplicationConfigManager
from ...config.manager import ConfigManager
from ...constants.general import SUF_PANEL_LEFT, TAG_TAB_RECONSTRUCTIONS
from ...constants.reconstructions import (
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
    LBL_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_LIST,
    LBL_CONTEXT_ITEM_RECONSTRUCTIONS_BROWSER_LOAD_RECONSTRUCTION,
    LBL_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS,
    LBL_TREE_RECONSTRUCTIONS_BROWSER_RECONSTRUCTIONS,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_DIRECTORY,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_RECONSTRUCT_FILE,
    TAG_BUTTON_RECONSTRUCTIONS_BROWSER_REFRESH_RECONSTRUCTIONS,
    TAG_GROUP_RECONSTRUCTIONS_BROWSER_CONTROLS,
    TAG_GROUP_RECONSTRUCTIONS_BROWSER_TREE,
    TAG_PANEL_RECONSTRUCTIONS_BROWSER,
    TAG_TREE_RECONSTRUCTIONS_BROWSER,
    TAG_WINDOW_RECONSTRUCTIONS_BROWSER_TREE,
)
from ...elements.button import GUIButton
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree.state import TreeNodeState
from ...elements.tree.tree import GUITreePanel
from ...reconstruction.browser import BrowserManager
from ...reconstruction.data import ReconstructionData
from ...reconstruction.manager import ReconstructionManager
from ...utils.dpg import dpg_configure_item

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

        self.load_reconstruction_with_confirmation: Optional[OnLoadReconstructionCallback] = None
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

    def _rebuild_tree(self) -> None:
        if self._building_tree:
            return

        self._building_tree = True
        try:
            self._delete_item_handler_registries()
            output_directory = self.config_manager.get_output_directory()
            self.browser_manager.set_output_directory(output_directory)
            self._handlers.clear()
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

    @traverse(TreeTraversal.BFS)
    def _build_tree_node(
        self,
        node: TreeNode,
        state: TreeNodeState,
    ) -> None:
        node_tag = self._generate_node_tag(node)
        if node.node_type == NodeType.ROOT:
            return

        if not isinstance(node, FileSystemNode):
            return

        is_favorite = node.node_type != NodeType.ROOT and self._is_node_favorite(node)
        state.has_favorite_ancestor |= is_favorite
        if node.node_type == NodeType.DIRECTORY:
            should_expand = self._should_expand_node(node)
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=state.parent,
                default_open=should_expand,
            ):
                self._apply_node_theme(
                    node_tag,
                    node,
                    has_favorite_ancestor=state.has_favorite_ancestor,
                )

            self._add_item_handler_registry(
                node_tag=node_tag,
                node=node,
                item_click_callback=self._on_directory_node_clicked,
            )
        else:
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=state.parent,
                leaf=True,
            ):
                self._apply_node_theme(
                    node_tag,
                    node,
                    has_favorite_ancestor=state.has_favorite_ancestor,
                )

            self._add_item_handler_registry(
                node_tag=node_tag,
                node=node,
                item_double_click_callback=self._on_reconstruction_node_clicked,
            )

        state.parent = node_tag

    def _set_tree_enabled(self, enabled: bool) -> None:
        dpg_configure_item(TAG_GROUP_RECONSTRUCTIONS_BROWSER_TREE, enabled=enabled)
        dpg_configure_item(TAG_GROUP_RECONSTRUCTIONS_BROWSER_CONTROLS, enabled=enabled)

    def _reconstruct_file(self) -> None:
        self.call(self.on_reconstruct_file)

    def _reconstruct_directory(self) -> None:
        self.call(self.on_reconstruct_directory)

    def _on_directory_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, _ = user_data
        if mouse_button == dpg.mvMouseButton_Right:
            return self._show_directory_context_menu(node)

        return None

    def _on_reconstruction_node_clicked(
        self,
        sender: Sender,
        app_data: Tuple[int, int],
        user_data: Tuple[FileSystemNode, str],
    ) -> None:
        mouse_button, _ = app_data
        node, node_tag = user_data
        if mouse_button == dpg.mvMouseButton_Left:
            self.call(self.load_reconstruction_with_confirmation, node.filepath)

        if mouse_button == dpg.mvMouseButton_Right:
            self._show_reconstruction_context_menu(node, node_tag)

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

    def _show_reconstruction_context_menu(self, node: FileSystemNode, node_tag: str) -> None:
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
                user_data=(node, node_tag),
            )
            dpg.add_separator()
            self._add_context_menu_favorite_item(node)

    def _on_load_reconstruction(self, sender: Sender, app_data: Path, user_data: FileSystemNode) -> None:
        self.call(self.load_reconstruction_with_confirmation, user_data.filepath)

    def lock(self) -> None:
        self._building_tree = True
        self._set_tree_enabled(False)

    def unlock(self) -> None:
        self._building_tree = False
        self._set_tree_enabled(True)

    @property
    def locked(self) -> bool:
        return self._building_tree
