from typing import Final, List

from sampletones_application.categories.elements.global_ import MenuElements
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items.viewport import read_viewport
from tests.suite.screens.environment import SCREEN_SIZE
from tests.suite.screens.screen import Screen
from tests.suite.screens.written import written_state

WHOLE_SCREEN: Final[Rect] = Rect(x=0, y=0, width=SCREEN_SIZE.width, height=SCREEN_SIZE.height)


def window(screen: Screen) -> Rect:
    """The rectangle the window fills on the screen."""
    return screen.bridge.ask(read_viewport)


def marked_fullscreen(screen: Screen) -> bool:
    """Whether View ▸ Fullscreen carries its check mark."""
    return screen.menu.is_checked(MenuElements.GROUP_VIEW, MenuElements.ITEM_VIEW_FULLSCREEN)


class TestFullscreen:
    """F11 fills the screen and F11 again gives the window back its size and place.

    The View menu's mark follows the window, and leaving the application from the windowed state writes
    a session that is not fullscreen. Two presses in a row end where they began.
    """

    def test_f11_fills_and_restores(self, screen: Screen) -> None:
        windowed: List[Rect] = []

        def f11_fills_the_screen(screen: Screen) -> None:
            windowed.append(window(screen))
            assert windowed[0] != WHOLE_SCREEN

            screen.press_shortcut(ShortcutId.TOGGLE_FULLSCREEN)

            screen.expect(lambda: window(screen), WHOLE_SCREEN.__eq__, description="the window filling the screen")
            assert marked_fullscreen(screen)

        def f11_again_restores_it(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.TOGGLE_FULLSCREEN)

            screen.expect(lambda: window(screen), windowed[0].__eq__, description="the window back where it stood")
            assert not marked_fullscreen(screen)

        def two_presses_at_once_end_where_they_began(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.TOGGLE_FULLSCREEN)
            screen.press_shortcut(ShortcutId.TOGGLE_FULLSCREEN)

            screen.expect(lambda: window(screen), windowed[0].__eq__, description="the window where it stood")
            assert not marked_fullscreen(screen)

        def leaving_writes_a_window(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.EXIT)

            assert screen.wait_for_exit()
            assert not written_state().viewport.fullscreen

        screen.scenario(
            f11_fills_the_screen,
            f11_again_restores_it,
            two_presses_at_once_end_where_they_began,
            leaving_writes_a_window,
        ).run()
