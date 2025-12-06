import dearpygui.dearpygui as dpg

from sampletones.tree import FileSystemNode, TreeNode
from sampletones.typehints import Sender

from ...constants import (
    DIM_PANEL_LEFT_HEIGHT,
    DIM_PANEL_LEFT_WIDTH,
    LBL_EXPLORER_FILESYSTEM,
    NOD_TYPE_DIRECTORY,
    TAG_EXPLORER_PANEL,
    TAG_EXPLORER_PANEL_GROUP,
    TAG_EXPLORER_TREE,
    TAG_EXPLORER_TREE_GROUP,
    TAG_EXPLORER_TREE_WINDOW,
)
from ...elements.fonts.font import Font
from ...elements.fonts.registry import FontRegistry
from ...elements.tree import GUITreePanel
from ...explorer.manager import ExplorerManager


class GUIExplorerPanel(GUITreePanel):
    def __init__(self):
        self.explorer_manager = ExplorerManager()

        super().__init__(
            tree=self.explorer_manager.tree,
            tag=TAG_EXPLORER_PANEL,
            parent=TAG_EXPLORER_PANEL_GROUP,
            width=DIM_PANEL_LEFT_WIDTH,
            height=DIM_PANEL_LEFT_HEIGHT,
        )

    def create_panel(self) -> None:
        with dpg.child_window(
            tag=self.tag,
            width=self.width,
            height=self.height,
            parent=self.parent,
        ):
            self._create_section_text()
            self._create_tree_window()

    def _create_section_text(self) -> None:
        section_text = dpg.add_text(LBL_EXPLORER_FILESYSTEM)
        FontRegistry.bind_to_item(section_text, Font.BOLD)

    def _create_tree_window(self) -> None:
        dpg.add_separator()
        self.create_search(self.tag)
        with dpg.child_window(tag=TAG_EXPLORER_TREE_WINDOW):
            with dpg.group(tag=TAG_EXPLORER_TREE_GROUP):
                with dpg.tree_node(label=LBL_EXPLORER_FILESYSTEM, tag=TAG_EXPLORER_TREE, default_open=True):
                    pass

    def initialize_tree(self) -> None:
        self._refresh_tree()

    def refresh(self) -> None:
        self._refresh_tree()

    def _rebuild_tree(self) -> None:
        self.build_tree(TAG_EXPLORER_TREE)

    def _refresh_tree(self) -> None:
        self._set_explorer_tree_enabled(False)
        self.explorer_manager.refresh_tree()
        self._rebuild_tree()
        self._set_explorer_tree_enabled(True)

    def _set_explorer_tree_enabled(self, enabled: bool) -> None:
        dpg.configure_item(TAG_EXPLORER_TREE_GROUP, enabled=enabled)

    def _build_tree_node(self, node: TreeNode, parent: str) -> None:
        node_tag = self._generate_node_tag(node)

        if not isinstance(node, FileSystemNode):
            return

        if node.node_type == NOD_TYPE_DIRECTORY:
            should_expand = self._should_expand_node(node) or self.explorer_manager.is_directory_expanded(node.filepath)
            with dpg.tree_node(
                label=node.name,
                tag=node_tag,
                parent=parent,
                default_open=should_expand,
                open_on_arrow=True,
            ) as tree_node_tag:
                FontRegistry.bind_to_item(node_tag, Font.REGULAR_SMALL)

                if self.explorer_manager.is_directory_expanded(node.filepath):
                    for child in node.children:
                        self._build_tree_node(child, node_tag)

                dpg.add_tree_node(
                    label="",
                    tag=f"{node_tag}_dummy",
                    parent=tree_node_tag,
                    show=not self.explorer_manager.is_directory_expanded(node.filepath),
                )

            handler_registry_tag = f"{node_tag}_handler"
            with dpg.item_handler_registry(tag=handler_registry_tag):
                dpg.add_item_clicked_handler(callback=self._on_directory_node_clicked, user_data=node)
            dpg.bind_item_handler_registry(node_tag, handler_registry_tag)

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

    def _on_directory_node_clicked(self, sender: Sender, app_data: int, user_data: FileSystemNode) -> None:
        if not isinstance(user_data, FileSystemNode) or user_data.node_type != NOD_TYPE_DIRECTORY:
            return

        node_tag = self._generate_node_tag(user_data)

        if not dpg.does_item_exist(node_tag):
            return

        is_open = dpg.get_value(node_tag)

        if is_open and not self.explorer_manager.is_directory_expanded(user_data.filepath):
            self.explorer_manager.expand_directory(user_data)

            dummy_tag = f"{node_tag}_dummy"
            if dpg.does_item_exist(dummy_tag):
                dpg.delete_item(dummy_tag)

            for child in user_data.children:
                self._build_tree_node(child, node_tag)
