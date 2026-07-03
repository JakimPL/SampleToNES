from unittest.mock import Mock, patch

from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager


class TestInputFocusTracking:
    def test_focus_event_marks_input_focused(self) -> None:
        manager = ShortcutManager()

        manager._on_input_focused(sender=1, app_data=42)

        assert manager.is_input_focused

    def test_unfocus_of_focused_widget_releases_focus(self) -> None:
        manager = ShortcutManager()
        manager._on_input_focused(sender=1, app_data=42)

        manager._on_input_unfocused(sender=1, app_data=42)

        assert not manager.is_input_focused

    def test_unfocus_of_other_widget_keeps_focus(self) -> None:
        manager = ShortcutManager()
        manager._on_input_focused(sender=1, app_data=42)

        manager._on_input_unfocused(sender=1, app_data=99)

        assert manager.is_input_focused


class TestKeyDispatchWhileInputFocused:
    def test_focused_input_suppresses_the_shortcut(self) -> None:
        manager = ShortcutManager()
        callback = Mock()
        manager._on_input_focused(sender=1, app_data=42)

        with patch.object(manager, "_modifiers_match", return_value=True):
            manager._handle_key(Mock(), callback)

        callback.assert_not_called()

    def test_released_input_restores_the_shortcut(self) -> None:
        manager = ShortcutManager()
        callback = Mock()
        manager._on_input_focused(sender=1, app_data=42)
        manager._on_input_unfocused(sender=1, app_data=42)

        with patch.object(manager, "_modifiers_match", return_value=True):
            manager._handle_key(Mock(), callback)

        callback.assert_called_once()
