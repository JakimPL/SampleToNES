from typing import Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON
from sampletones_application.tags.graphs import SUF_GRAPH_Y_AXIS
from sampletones_application.tags.instructions import (
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_SPECTRUM,
    TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_WAVEFORM,
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_CANCEL_GENERATION,
    TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY,
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REBUILD_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_DIALOG_REGENERATE_CONFIRMATION,
    TAG_INSTRUCTIONS_LIBRARY_PANEL,
    TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS,
    TAG_INSTRUCTIONS_LIBRARY_TREE,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import Item, read_label, read_value
from tests.suite.screens.views.browsers import FileTree
from tests.suite.screens.views.notices import Notice
from tests.suite.screens.views.prompts import Prompt
from tests.suite.screens.views.waveform import Waveform

GENERATE_BUTTON = compose_tag(TAG_INSTRUCTIONS_LIBRARY_BUTTON_GENERATE_LIBRARY, SUF_BUTTON)
CANCEL_GENERATION_BUTTON = compose_tag(TAG_INSTRUCTIONS_LIBRARY_BUTTON_CANCEL_GENERATION, SUF_BUTTON)
SPECTRUM_BANDS = compose_tag(TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_SPECTRUM, SUF_GRAPH_Y_AXIS)
BAR_SERIES_TYPE: Final[str] = "mvAppItemType::mvBarSeries"


class Library:
    """The Instructions tab's library card: the libraries its folder holds, and the line saying where they stand."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self.tree = FileTree(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_TREE)
        self.rebuild_prompt = Prompt(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_DIALOG_REBUILD_CONFIRMATION)
        self.regenerate_prompt = Prompt(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_DIALOG_REGENERATE_CONFIRMATION)
        self.notice = Notice(bridge, hand, TAG_INSTRUCTIONS_LIBRARY_PANEL)

    def row(self, filename: str) -> Optional[Item]:
        """The row standing for the library stored under ``filename``, if one is drawn."""
        return self.tree.library_row(lambda node: node.library_key.filename == filename)

    def generate_label(self) -> str:
        """What the button generating a library reads: Generate, or Regenerate where the library stands."""
        return self._bridge.ask(lambda: read_label(GENERATE_BUTTON))

    def generate(self) -> None:
        self._hand.scroll_into_view(GENERATE_BUTTON)
        self._hand.click(GENERATE_BUTTON)

    def cancel_generation(self) -> None:
        self._hand.click(CANCEL_GENERATION_BUTTON)

    def status(self) -> str:
        """What the line under the tree says about the library in hand."""
        return str(self._bridge.ask(lambda: read_value(TAG_INSTRUCTIONS_LIBRARY_TEXT_STATUS)))


class Instructions:
    """The Instructions tab: the library card, and the waveform and spectrum of the instruction picked in it."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self.library = Library(bridge, hand)
        self.waveform = Waveform(bridge, hand, TAG_INSTRUCTIONS_INSTRUCTION_PANEL_INSTRUCTION_WAVEFORM)

    def spectrum_bands(self) -> int:
        """How many bands the spectrum draws."""

        def read() -> int:
            return sum(
                1
                for child in dpg.get_item_children(SPECTRUM_BANDS, 1)
                if dpg.get_item_info(child)["type"] == BAR_SERIES_TYPE
            )

        return self._bridge.ask(read)
