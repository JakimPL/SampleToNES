import operator
from typing import Final

import pytest

from tests.screens.interface.display.steps import (
    another_size,
    at_its_own_size_and_place,
    framed,
    hand_sized_world,
    kept,
    open_display_settings,
    size_named,
    window_size,
)
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World

COUNTDOWN_LIMIT_SECONDS: Final[float] = 20.0
SETTLING_FRAMES: Final[int] = 10


class TestTheWindowModeCountdown:
    """A window change counts down: Keep keeps it, while Revert and the count running out bring the window
    back. Cancel then puts back the window the dialog opened with.

    The scenario switches to a frameless window and presses Revert, switches again and lets the
    countdown run out, then switches once more, presses Keep, and cancels the dialog, expecting the
    frame back.
    """

    def test_keep_revert_and_running_out(self, screen: Screen) -> None:
        settings = screen.display_settings

        def revert_brings_the_frame_back(screen: Screen) -> None:
            open_display_settings(screen)
            settings.toggle_borderless()
            screen.expect(settings.countdown_shown, bool, description="the countdown")
            assert not framed(screen)

            settings.revert()

            screen.expect(settings.countdown_shown, operator.not_, description="the countdown gone")
            screen.expect(lambda: framed(screen), bool, description="the frame back")
            assert not settings.borderless()

        def running_out_brings_it_back(screen: Screen) -> None:
            settings.toggle_borderless()
            screen.expect(settings.countdown_shown, bool, description="the countdown")

            screen.bridge.expect(
                settings.countdown_shown,
                operator.not_,
                description="the countdown run out",
                timeout=COUNTDOWN_LIMIT_SECONDS,
            )

            screen.expect(lambda: framed(screen), bool, description="the frame back")
            assert not settings.borderless()

        def keep_keeps_it_until_cancel(screen: Screen) -> None:
            settings.toggle_borderless()

            kept(screen)

            screen.frames(SETTLING_FRAMES)
            assert not framed(screen)
            assert settings.borderless()
            settings.cancel()
            screen.expect(settings.discard_prompt.is_shown, bool, description="the question about the change")
            settings.discard_prompt.confirm()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            screen.expect(lambda: framed(screen), bool, description="the frame back")

        screen.scenario(revert_brings_the_frame_back, running_out_brings_it_back, keep_keeps_it_until_cancel).run()


class TestTheCountdownOnAHandSizedWindow:
    """Revert and the count running out put a window the user sized by hand back at its own size and place,
    as Cancel does.

    The window opens between the sizes Display settings offers. The scenario picks another size and presses
    Revert, then picks it again and lets the countdown run out, expecting the window back where it opened
    each time, and Cancel then closes the dialog with the window still there.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home whose window the user sized by hand, between the sizes Display settings offers."""
        return hand_sized_world()

    def test_revert_and_running_out_put_back_the_window_s_own_size(self, screen: Screen) -> None:
        settings = screen.display_settings

        def another_size_on_screen(screen: Screen) -> None:
            label = another_size(screen)
            settings.choose_resolution(label)
            screen.expect(settings.countdown_shown, bool, description="the countdown")
            screen.expect(
                lambda: window_size(screen),
                (size_named(label).width, size_named(label).height).__eq__,
                description="the window at the size picked",
            )

        def revert_puts_it_back(screen: Screen) -> None:
            open_display_settings(screen)
            another_size_on_screen(screen)

            settings.revert()

            screen.expect(settings.countdown_shown, operator.not_, description="the countdown gone")
            at_its_own_size_and_place(screen)

        def running_out_puts_it_back(screen: Screen) -> None:
            another_size_on_screen(screen)

            screen.bridge.expect(
                settings.countdown_shown,
                operator.not_,
                description="the countdown run out",
                timeout=COUNTDOWN_LIMIT_SECONDS,
            )

            at_its_own_size_and_place(screen)

        def cancel_leaves_it_there(screen: Screen) -> None:
            settings.cancel()

            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            at_its_own_size_and_place(screen)

        screen.scenario(revert_puts_it_back, running_out_puts_it_back, cancel_leaves_it_there).run()
