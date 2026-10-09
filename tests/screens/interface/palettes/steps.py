from automation.dearpygui.items.colors import read_held_colors
from automation.palettes import in_fractions
from automation.screen import Screen
from automation.steps.reconstructions import expect_open
from tests.screens.interface.palettes.cases import Painted
from tests.screens.interface.palettes.constants import EVERY_TAB, TAB_FRAMES
from tests.suite.screens.worlds.recordings import PLAYABLE_RECONSTRUCTION


def painted(screen: Screen) -> Painted:
    """Reads every held color and every table highlight on the screen now."""
    return Painted(
        held=screen.bridge.ask(read_held_colors),
        highlights={place: in_fractions(color) for place, color in screen.table_highlights().items()},
    )


def show_every_tab(screen: Screen) -> None:
    """Brings each tab forward once, so every panel stands built and drawn before the colors are read."""
    expect_open(screen, PLAYABLE_RECONSTRUCTION)
    for tab in EVERY_TAB:
        screen.tabs.bring_to_front(tab)
        screen.frames(TAB_FRAMES)
