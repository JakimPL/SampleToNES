import operator
from typing import Final, List

import pytest

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.display import DisplayConfig
from sampletones_application.config.session.state.window import ViewportState
from sampletones_shared.display import Resolution
from tests.screens.interface.display.steps import (
    another_size,
    framed,
    kept,
    leave,
    open_display_settings,
    size_named,
    window_size,
)
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World, screen_filling_state
from tests.suite.screens.written import written_application_config, written_state

SEEDED_SIZE: Final[Resolution] = Resolution(width=1280, height=800)


class TestLeavingWritesTheWindowMode:
    """A window size and a frameless window, kept on the countdown and confirmed with OK, are what leaving
    writes.
    """

    def test_the_size_and_the_frame_are_written(self, screen: Screen) -> None:
        settings = screen.display_settings
        chosen: List[Resolution] = []

        def pick_a_size_and_keep_it(screen: Screen) -> None:
            open_display_settings(screen)
            label = another_size(screen)

            settings.choose_resolution(label)
            kept(screen)

            chosen.append(size_named(label))
            screen.expect(
                lambda: window_size(screen),
                (chosen[0].width, chosen[0].height).__eq__,
                description="the window at the size picked",
            )

        def go_frameless_and_keep_it(screen: Screen) -> None:
            assert framed(screen)

            settings.toggle_borderless()
            kept(screen)

            screen.expect(lambda: framed(screen), operator.not_, description="the window without its frame")

        def confirm_and_leave(screen: Screen) -> None:
            settings.confirm()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")

            leave(screen)

            viewport = written_state().viewport
            assert (viewport.width, viewport.height) == (chosen[0].width, chosen[0].height)
            assert written_application_config().display.borderless

        screen.scenario(pick_a_size_and_keep_it, go_frameless_and_keep_it, confirm_and_leave).run()


class TestAHomeHoldingAWindowModeShowsIt:
    """A home whose session holds a window size and whose settings ask for a frameless window without
    vertical sync opens the application that way, and Display settings shows it.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home with a 1280 by 800 window at the screen's corner, frameless and without vertical sync."""
        state = screen_filling_state().model_copy(
            update={"viewport": ViewportState(width=SEEDED_SIZE.width, height=SEEDED_SIZE.height, x=0, y=0)}
        )
        return World(
            state=state,
            application_config=ApplicationConfig(display=DisplayConfig(borderless=True, vsync=False)),
            config=None,
            files=(),
        )

    def test_the_window_opens_as_the_session_left_it(self, screen: Screen) -> None:
        """The window opens at the written size without its frame, and Display settings names the size, the
        frameless mode and the vertical sync setting.
        """
        settings = screen.display_settings

        def the_window_stands_as_written(screen: Screen) -> None:
            assert window_size(screen) == (SEEDED_SIZE.width, SEEDED_SIZE.height)
            assert not framed(screen)

        def display_settings_names_it(screen: Screen) -> None:
            open_display_settings(screen)

            assert settings.resolution() == str(SEEDED_SIZE)
            assert settings.borderless()
            assert not settings.vsync()
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")

        screen.scenario(the_window_stands_as_written, display_settings_names_it).run()
