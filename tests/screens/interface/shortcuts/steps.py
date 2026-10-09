from automation.screen import Screen
from sampletones_application.categories.hierarchy import Tab
from tests.screens.interface.shortcuts.constants import SETTLING_FRAMES


def on_a_tab(screen: Screen, tab: Tab) -> None:
    """Brings ``tab`` forward with a click, which leaves every field free of the keyboard."""
    screen.tabs.bring_to_front(tab)
    screen.frames(SETTLING_FRAMES)
