from typing import Dict, Final

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.tags.general import (
    TAG_GLOBAL_TAB_INSTRUCTIONS,
    TAG_GLOBAL_TAB_MAIN,
    TAG_GLOBAL_TAB_RECONSTRUCTION,
    TAG_GLOBAL_TAB_SEQUENCER,
    TAG_GLOBAL_TABS,
)
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_selected_tab

TAB_TAGS: Final[Dict[Tab, str]] = {
    Tab.MAIN: TAG_GLOBAL_TAB_MAIN,
    Tab.RECONSTRUCTIONS: TAG_GLOBAL_TAB_RECONSTRUCTION,
    Tab.SEQUENCER: TAG_GLOBAL_TAB_SEQUENCER,
    Tab.INSTRUCTIONS: TAG_GLOBAL_TAB_INSTRUCTIONS,
}
TABS_BY_TAG: Final[Dict[str, Tab]] = {tag: tab for tab, tag in TAB_TAGS.items()}


class Tabs:
    """The tab bar across the window: which tab stands in front, and the headers that bring one forward."""

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
    ) -> None:
        self._bridge = bridge
        self._hand = hand

    def bring_to_front(self, tab: Tab) -> None:
        """Clicks the header of ``tab``."""
        self._hand.click(TAB_TAGS[tab])

    def front(self) -> Tab:
        """The tab standing in front."""
        return TABS_BY_TAG[self._bridge.ask(lambda: read_selected_tab(TAG_GLOBAL_TABS))]
