from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import forgive_the_hover_race


def leaving_asks_nothing(screen: Screen) -> None:
    """Exits a project left as it was opened, which goes through at once."""
    forgive_the_hover_race(screen)
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()
