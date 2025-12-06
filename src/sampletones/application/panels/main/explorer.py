import dearpygui.dearpygui as dpg

from ...constants import (
    DIM_PANEL_LEFT_HEIGHT,
    DIM_PANEL_LEFT_WIDTH,
    LBL_EXPLORER_FILESYSTEM,
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
