import operator

from automation.screen import Screen
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId


def open_audio_settings(screen: Screen) -> None:
    """Opens Audio settings from its shortcut and waits for it."""
    screen.press_shortcut(ShortcutId.AUDIO_SETTINGS)
    screen.expect(screen.audio_settings.is_shown, bool, description="Audio settings")


class TestApplyingWithNoDevice:
    """With no output device to pick, Apply in Audio settings closes the window and changes nothing.

    Apply closes the window and reports no error. Audio settings then opens again, and Cancel closes
    it, which shows the first Apply left the dialog answering as before.
    """

    def test_apply_closes_the_window(self, screen: Screen) -> None:
        """The window closes on Apply, and opens and closes again afterwards."""
        settings = screen.audio_settings

        def apply_closes_the_window(screen: Screen) -> None:
            open_audio_settings(screen)

            settings.apply()

            screen.expect(settings.is_shown, operator.not_, description="Audio settings closed")
            assert not screen.error_notice.is_shown()

        def the_window_opens_again(screen: Screen) -> None:
            open_audio_settings(screen)

            screen.press_shortcut(ShortcutId.DIALOG_CANCEL)

            screen.expect(settings.is_shown, operator.not_, description="Audio settings closed")

        screen.scenario(apply_closes_the_window, the_window_opens_again).run()
