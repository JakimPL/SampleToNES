from pathlib import Path
from typing import Callable, List, Optional

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.dearpygui.items.reading import find_item
from automation.dearpygui.items.texts import read_label
from automation.dearpygui.items.types import TREE_NODE_TYPE, Item
from automation.dearpygui.keys import IMGUI_LEFT_CTRL
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.structures.tree.node import (
    FileSystemNode,
    GeneratorNode,
    LibraryNode,
    TreeNode,
)

NodeTest = Callable[[TreeNode], bool]


class FileTree:
    """A tree of rows on one of the tabs, each row standing for the node of the tree it was drawn from.

    A row carries its node, so the view finds a row by the file or the library the node names,
    and a heading by the words it shows.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tree: str,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._tree = tree

    def file_row(self, path: Path) -> Optional[Item]:
        """The first row naming the file or folder at ``path``, if one is drawn."""
        return self._row(lambda node: isinstance(node, FileSystemNode) and node.filepath == path)

    def generator_row(self, generator: GeneratorName) -> Optional[Item]:
        """The first row standing for ``generator``, if one is drawn."""
        return self._row(lambda node: isinstance(node, GeneratorNode) and node.generator_name == generator)

    def library_row(self, matches: Callable[[LibraryNode], bool]) -> Optional[Item]:
        """The first row standing for a library ``matches`` accepts, if one is drawn."""
        return self._row(lambda node: isinstance(node, LibraryNode) and matches(node))

    def heading(self, label: str) -> Optional[Item]:
        """The first row whose words read ``label``, such as a heading the tree groups its files under."""
        return self._bridge.ask(
            lambda: find_item(
                self._tree,
                lambda item: _is_tree_row(item) and read_label(item).strip() == label.strip(),
            )
        )

    def label(self, row: Item) -> str:
        """The words ``row`` reads."""
        return self._bridge.ask(lambda: read_label(row))

    def rows_above(self, row: Item) -> List[Item]:
        """The rows ``row`` stands under, outermost first."""

        def read() -> List[Item]:
            above: List[Item] = []
            parent = dpg.get_item_parent(row)
            while parent is not None and dpg.get_item_alias(parent) != self._tree:
                if _is_tree_row(parent):
                    above.append(parent)
                parent = dpg.get_item_parent(parent)

            return above[::-1]

        return self._bridge.ask(read)

    def is_open(self, row: Item) -> bool:
        """Whether ``row`` stands open onto the rows under it."""
        return bool(self._bridge.ask(lambda: dpg.get_value(row)))

    def open_by_click(self, row: Item) -> None:
        """Brings ``row`` into view and clicks it, which opens or closes a row of a tree opened by a click."""
        self._hand.scroll_into_view(row)
        self._hand.click(row)

    def click(self, row: Item) -> None:
        """Brings ``row`` into view and clicks it."""
        self._hand.scroll_into_view(row)
        self._hand.click(row)

    def double_click(self, row: Item) -> None:
        """Brings ``row`` into view and double-clicks it."""
        self._hand.scroll_into_view(row)
        self._hand.double_click(row)

    def ctrl_click(self, row: Item) -> None:
        """Brings ``row`` into view and clicks it while holding Ctrl."""
        self._hand.scroll_into_view(row)
        self._hand.click_holding(row, [IMGUI_LEFT_CTRL])

    def right_click(self, row: Item) -> None:
        """Brings ``row`` into view and clicks it with the right button, which opens its menu."""
        self._hand.scroll_into_view(row)
        self._hand.right_click(row)

    def _row(self, matches: NodeTest) -> Optional[Item]:
        return self._bridge.ask(
            lambda: find_item(
                self._tree,
                lambda item: _is_tree_row(item) and _node_matches(item, matches),
            )
        )


def _is_tree_row(item: Item) -> bool:
    return str(dpg.get_item_info(item)["type"]) == TREE_NODE_TYPE


def _node_matches(item: Item, matches: NodeTest) -> bool:
    user_data = dpg.get_item_user_data(item)
    if not isinstance(user_data, tuple) or not user_data:
        return False

    node = user_data[0]
    return isinstance(node, TreeNode) and bool(matches(node))
