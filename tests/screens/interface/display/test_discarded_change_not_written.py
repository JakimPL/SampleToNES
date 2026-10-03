import operator
from typing import List

from tests.screens.application.restart.steps import leave
from tests.suite.screens.screen import Screen
from tests.suite.screens.written import written_application_config


class TestADiscardedDisplayChange:
    """A Display settings change thrown away stays out of the written settings, while one confirmed is
    written.

    The scenario flips vertical sync and discards it, flips it again and confirms, leaves the
    application, and expects the written settings to hold the confirmed value.
    """

    def test_leaving_writes_only_the_confirmed_change(self, screen: Screen) -> None:
        settings = screen.display_settings
        prompt = settings.discard_prompt
        original: List[bool] = []

        def discard_a_change(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the Display settings dialog")
            original.append(settings.vsync())
            settings.toggle_vsync()
            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

            settings.cancel()
            screen.expect(prompt.is_shown, bool, description="the discard prompt")
            prompt.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")

        def confirm_a_change(screen: Screen) -> None:
            settings.open()
            screen.expect(settings.is_shown, bool, description="the dialog open again")
            assert settings.vsync() == original[0]
            settings.toggle_vsync()
            screen.expect(settings.vsync, original[0].__ne__, description="the box flipped")

            settings.confirm()

            screen.expect(settings.is_shown, operator.not_, description="the dialog closed")

        def leaving_writes_the_confirmed_one(screen: Screen) -> None:
            leave(screen)

            assert written_application_config().display.vsync is not original[0]

        screen.scenario(discard_a_change, confirm_a_change, leaving_writes_the_confirmed_one).run()
