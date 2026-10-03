from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.screen import Screen


def tab(screen: Screen, times: int) -> None:
    """Presses the shortcut for the next control in a dialog ``times`` times."""
    for _ in range(times):
        screen.press_shortcut(ShortcutId.DIALOG_NEXT_CONTROL)


def enter(screen: Screen) -> None:
    """Presses the shortcut that activates the focused control of a dialog."""
    screen.press_shortcut(ShortcutId.DIALOG_ACTIVATE)


def escape(screen: Screen) -> None:
    """Presses the shortcut that cancels a dialog."""
    screen.press_shortcut(ShortcutId.DIALOG_CANCEL)
