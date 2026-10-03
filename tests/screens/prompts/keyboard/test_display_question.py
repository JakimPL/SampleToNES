import operator
from typing import List

from tests.screens.prompts.keyboard.steps import enter, escape, tab
from tests.suite.screens.screen import Screen


class TestTheDisplayQuestionFromTheKeyboard:
    """The question Escape asks of changed Display settings answers to the keys, as does the dialog after it.

    The user flips Vertical sync and presses Escape. Enter keeps the dialog open with the change. Escape
    again, then Tab and Enter, discards the change; the dialog reopens with the original value.
    """

    def test_enter_keeps_editing_and_tab_enter_discards(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt
        original: List[bool] = []

        def change_vertical_sync(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the Display settings dialog")
            original.append(settings.vsync())

            settings.toggle_vsync()

            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

        def escape_asks(screen: Screen) -> None:
            escape(screen)

            screen.expect(prompt.is_shown, bool, description="the discard question")

        def enter_keeps_editing(screen: Screen) -> None:
            enter(screen)

            screen.expect(settings.is_shown, bool, description="the dialog back")
            assert not prompt.is_shown()
            assert settings.vsync() != original[0]

        def escape_then_tab_and_enter_discard(screen: Screen) -> None:
            escape(screen)
            screen.expect(prompt.is_shown, bool, description="the discard question again")

            tab(screen, 1)
            enter(screen)

            screen.expect(prompt.is_shown, operator.not_, description="the question gone")
            assert not settings.is_shown()
            settings.open()
            screen.expect(settings.is_shown, bool, description="the dialog opened again")
            assert settings.vsync() == original[0]
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="the unchanged dialog closed")

        screen.scenario(change_vertical_sync, escape_asks, enter_keeps_editing, escape_then_tab_and_enter_discard).run()
