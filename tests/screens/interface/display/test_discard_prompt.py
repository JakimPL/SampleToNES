import operator
from typing import Final, List

import pytest

from sampletones_application.config.session.state.state import ApplicationState
from sampletones_application.config.session.state.window import ViewportState
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.display import Resolution
from tests.screens.interface.display.steps import (
    another_size,
    kept,
    open_display_settings,
    size_named,
    window_position,
    window_size,
)
from tests.suite.screens.screen import Screen
from tests.suite.screens.worlds.home import World

HAND_SIZE: Final[Resolution] = Resolution(width=1300, height=820)
HAND_X: Final[int] = 100
HAND_Y: Final[int] = 60


class TestDiscardingADisplayChange:
    """Cancelling Display settings with a change pending asks before the change is thrown away.

    The scenario flips vertical sync and cancels. Keep editing returns to the dialog with the change
    in place. Cancel and discard close it, and the dialog reopens with the original value.
    """

    def test_keep_editing_brings_the_dialog_back_and_discard_restores_it(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt
        original: List[bool] = []

        def change_vertical_sync(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the Display settings dialog")
            original.append(settings.vsync())

            settings.toggle_vsync()

            screen.expect(settings.vsync, original[0].__ne__, description="the vertical sync box flipped")

        def cancel_asks_first(screen: Screen) -> None:
            settings.cancel()

            screen.expect(prompt.is_shown, bool, description="the discard prompt")
            assert not settings.is_shown()

        def keep_editing(screen: Screen) -> None:
            prompt.cancel()

            screen.expect(settings.is_shown, bool, description="the dialog back on the screen")
            assert not prompt.is_shown()
            assert settings.vsync() != original[0]

        def discard(screen: Screen) -> None:
            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt again")

            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")
            assert not prompt.is_shown()

        def reopen_as_it_was(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the dialog open again")

            assert settings.vsync() == original[0]

            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="the unchanged dialog closed at once")

        screen.scenario(
            change_vertical_sync,
            cancel_asks_first,
            keep_editing,
            discard,
            reopen_as_it_was,
        ).run()


class TestTheKeyboardOnDisplaySettings:
    """The keys alone answer Display settings."""

    def test_escape_closes_an_unchanged_dialog(self, screen: Screen) -> None:
        """Escape closes a dialog that holds no change, with no question."""
        settings = screen.display_settings
        settings.open()
        screen.expect(settings.is_shown, bool, description="the Display settings dialog")

        screen.press_shortcut(ShortcutId.DIALOG_CANCEL)

        screen.expect(settings.is_shown, operator.not_, description="the dialog closed")
        assert not settings.discard_prompt.is_shown()


class TestDiscardingOnAHandSizedWindow:
    """Discarding a new size puts a window the user sized by hand back at its own size and place.

    The window opens between the sizes Display settings offers, so the dialog names the offered size
    nearest it. The scenario keeps another size and discards it, and expects the window back at the
    size and place it opened with.
    """

    @pytest.fixture
    def world(self) -> World:
        """A home whose window the user sized by hand, between the sizes Display settings offers."""
        return World(
            state=ApplicationState(
                viewport=ViewportState(
                    width=HAND_SIZE.width,
                    height=HAND_SIZE.height,
                    x=HAND_X,
                    y=HAND_Y,
                )
            ),
            application_config=None,
            config=None,
            files=(),
        )

    def test_discarding_puts_back_the_window_s_own_size(self, screen: Screen) -> None:
        """The window stands at its own size and place once the new size is discarded."""
        settings = screen.display_settings
        prompt = settings.discard_prompt

        def a_size_between_the_offered_ones(screen: Screen) -> None:
            assert window_size(screen) == (HAND_SIZE.width, HAND_SIZE.height)
            assert window_position(screen) == (HAND_X, HAND_Y)

            open_display_settings(screen)

            assert HAND_SIZE not in [size_named(label) for label in settings.resolutions()]
            assert size_named(settings.resolution()) != HAND_SIZE

        def keep_another_size(screen: Screen) -> None:
            label = another_size(screen)

            settings.choose_resolution(label)
            kept(screen)

            screen.expect(
                lambda: window_size(screen),
                (size_named(label).width, size_named(label).height).__eq__,
                description="the window at the size picked",
            )

        def discard_it(screen: Screen) -> None:
            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt")

            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")
            screen.expect(
                lambda: window_size(screen),
                (HAND_SIZE.width, HAND_SIZE.height).__eq__,
                description="the window at its own size",
            )
            assert window_position(screen) == (HAND_X, HAND_Y)

        screen.scenario(a_size_between_the_offered_ones, keep_another_size, discard_it).run()
