import operator
from typing import List

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.suite.screens.screen import Screen


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
