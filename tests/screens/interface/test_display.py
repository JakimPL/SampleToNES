import operator
from typing import Final, List, Tuple

import pytest

from sampletones_application.config.session.application.config import ApplicationConfig
from sampletones_application.config.session.application.display import DisplayConfig
from sampletones_application.config.session.state.window import ViewportState
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.display import Resolution
from tests.suite.screens.dearpygui.items import read_viewport, read_viewport_decorated
from tests.suite.screens.screen import Screen
from tests.suite.screens.world import World, screen_filling_state
from tests.suite.screens.written import written_application_config, written_state

SIZE_SEPARATOR: Final[str] = "x"
SEEDED_SIZE: Final[Resolution] = Resolution(width=1280, height=800)
COUNTDOWN_LIMIT_SECONDS: Final[float] = 20.0
SETTLING_FRAMES: Final[int] = 10


def size_named(label: str) -> Resolution:
    """The window size a Resolution entry names, written width first."""
    width, height = label.split(SIZE_SEPARATOR)
    return Resolution(width=int(width), height=int(height))


def window_size(screen: Screen) -> Tuple[int, int]:
    viewport = screen.bridge.ask(read_viewport)
    return round(viewport.width), round(viewport.height)


def framed(screen: Screen) -> bool:
    return screen.bridge.ask(read_viewport_decorated)


def open_display_settings(screen: Screen) -> None:
    settings = screen.display_settings
    settings.open()
    screen.expect(settings.is_shown, bool, description="Display settings")


def another_size(screen: Screen) -> str:
    """A size the Resolution list offers other than the one it names."""
    settings = screen.display_settings
    current = settings.resolution()
    return next(label for label in settings.resolutions() if label != current)


def kept(screen: Screen) -> None:
    """Waits for the countdown a window change starts, and presses Keep."""
    settings = screen.display_settings
    screen.expect(settings.countdown_shown, bool, description="the countdown")
    settings.keep()
    screen.expect(settings.countdown_shown, operator.not_, description="the countdown gone")


def leave(screen: Screen) -> None:
    screen.press_shortcut(ShortcutId.EXIT)

    assert screen.wait_for_exit()


class TestLeavingWritesTheWindowMode:
    """A window size and a frameless window, kept on the countdown and confirmed with OK, are what leaving writes."""

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
    """A home whose session holds a window size and whose settings ask for a frameless window without vsync opens
    the application that way, and Display settings names it.
    """

    @pytest.fixture
    def world(self) -> World:
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


class TestTheWindowModeCountdown:
    """A window change counts down: Keep keeps it, while Revert, and the count running out, bring the window back;
    Cancel then puts back the window the dialog opened with.
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


class TestClosingWithASizeKeptButNotConfirmed:
    """The window closed while Display settings holds a size kept on the countdown but never confirmed: the session
    keeps the size the dialog opened with, as it does for every setting the dialog has not committed.
    """

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: closing the window writes a size Display settings never confirmed",
    )
    def test_leaving_writes_the_confirmed_size(self, screen: Screen) -> None:
        settings = screen.display_settings
        opened: List[Tuple[int, int]] = []

        def keep_a_size_without_confirming_it(screen: Screen) -> None:
            opened.append(window_size(screen))
            open_display_settings(screen)
            label = another_size(screen)

            settings.choose_resolution(label)
            kept(screen)

            screen.expect(
                lambda: window_size(screen),
                (size_named(label).width, size_named(label).height).__eq__,
                description="the window at the size picked",
            )

        def close_the_window(screen: Screen) -> None:
            screen.close_window()

            assert screen.wait_for_exit()
            viewport = written_state().viewport
            assert (viewport.width, viewport.height) == opened[0]

        screen.scenario(keep_a_size_without_confirming_it, close_the_window).run()
