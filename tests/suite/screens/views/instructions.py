from typing import Optional

from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REBUILD_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS,
    TAG_INSTRUCTIONS_LIBRARY_TREE,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import Item, read_value
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.prompts import Prompt


class Library:
    """The Instructions tab's library card: the libraries its folder holds, and the line saying where they stand."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self.tree = FileTree(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_TREE)
        self.rebuild_prompt = Prompt(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_DIALOG_REBUILD_CONFIRMATION)

    def row(self, filename: str) -> Optional[Item]:
        """The row standing for the library stored under ``filename``, if one is drawn."""
        return self.tree.library_row(lambda node: node.library_key.filename == filename)

    def status(self) -> str:
        """What the line under the tree says about the library in hand."""
        return str(self._bridge.ask(lambda: read_value(TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS)))


class Instructions:
    """The Instructions tab, as far as scenarios read it."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self.library = Library(bridge, hand)
