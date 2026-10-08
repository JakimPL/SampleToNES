import operator

import pytest

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.display import DisplayConfig
from tests.screens.interface.display.steps import leave, open_display_settings
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World, screen_filling_state
from tests.suite.screens.written import written_application_config


class TestSwitchingTheFrameRateReadingOff:
    """Unticking Show frame rate takes the reading off the menu bar at once, and leaving writes the choice.

    The scenario opens Display settings, unticks the box, sees the reading go, and confirms. The
    settings file it leaves behind asks for no reading.
    """

    def test_the_reading_goes_at_once_and_the_choice_is_written(self, screen: Screen) -> None:
        settings = screen.display_settings

        def untick_the_box(screen: Screen) -> None:
            assert screen.menu.frame_rate_reading_shown()
            open_display_settings(screen)
            assert settings.frame_rate_shown()

            settings.toggle_frame_rate()

            screen.expect(screen.menu.frame_rate_reading_shown, operator.not_, description="the reading gone")
            assert not settings.frame_rate_shown()

        def confirm_and_leave(screen: Screen) -> None:
            settings.confirm()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            assert not screen.menu.frame_rate_reading_shown()

            leave(screen)

            assert not written_application_config().display.show_frame_rate

        screen.scenario(untick_the_box, confirm_and_leave).run()


class TestDiscardingTheSwitchPutsTheReadingBack:
    """A switch of Show frame rate that is discarded leaves the reading as it stood, and the file untouched.

    The scenario unticks the box, cancels and discards: the reading comes back. It then unticks the
    box once more and confirms, so the file it leaves shows that the first switch wrote nothing and the
    second did.
    """

    def test_discard_restores_the_reading_and_a_confirmed_switch_writes(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt

        def untick_and_discard(screen: Screen) -> None:
            open_display_settings(screen)
            settings.toggle_frame_rate()
            screen.expect(screen.menu.frame_rate_reading_shown, operator.not_, description="the reading gone")

            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt")
            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")
            screen.expect(screen.menu.frame_rate_reading_shown, bool, description="the reading back")

        def untick_and_confirm(screen: Screen) -> None:
            open_display_settings(screen)
            assert settings.frame_rate_shown()

            settings.toggle_frame_rate()
            settings.confirm()

            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")
            assert not screen.menu.frame_rate_reading_shown()

        def leave_and_read_the_file(screen: Screen) -> None:
            leave(screen)

            assert not written_application_config().display.show_frame_rate

        screen.scenario(untick_and_discard, untick_and_confirm, leave_and_read_the_file).run()


class TestAHomeAskingForNoReadingOpensWithoutIt:
    """A home whose settings ask for no frame-rate reading opens the application without one, and Display
    settings shows the box unticked.

    Ticking the box puts the reading on the bar at once, and discarding that takes it off again.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home whose settings ask for no frame-rate reading."""
        return World(
            state=screen_filling_state(),
            application_config=ApplicationConfig(display=DisplayConfig(show_frame_rate=False)),
            config=None,
            files=(),
        )

    def test_the_reading_stays_off_until_asked_for(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt

        def no_reading_at_start(screen: Screen) -> None:
            assert not screen.menu.frame_rate_reading_shown()
            open_display_settings(screen)

            assert not settings.frame_rate_shown()

        def tick_the_box_and_discard(screen: Screen) -> None:
            settings.toggle_frame_rate()
            screen.expect(screen.menu.frame_rate_reading_shown, bool, description="the reading on the bar")

            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt")
            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")
            screen.expect(screen.menu.frame_rate_reading_shown, operator.not_, description="the reading off again")

        screen.scenario(no_reading_at_start, tick_the_box_and_discard).run()
