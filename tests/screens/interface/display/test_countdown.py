import operator
from typing import Final

from tests.screens.interface.display.steps import framed, kept, open_display_settings
from tests.suite.screens.screen import Screen

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
