from typing import Any, Callable, Dict, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.constants.general import TAG_HANDLER_GLOBAL_FOCUS
from sampletones_application.utils.shortcuts.keys import Modifier
from sampletones_application.utils.shortcuts.shortcut import Shortcut, ShortcutId
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    def __init__(self) -> None:
        self._shortcuts: Dict[ShortcutId, Tuple[Shortcut, Callback]] = {}
        self._enabled: bool = True

        self._handler_registry: Optional[int] = None
        self._focus_handler_tag = TAG_HANDLER_GLOBAL_FOCUS

    def register(self, shortcut_id: ShortcutId, shortcut: Shortcut, callback: Callback) -> None:
        self._shortcuts[shortcut_id] = (shortcut, callback)

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def get_shortcut_display(self, shortcut_id: ShortcutId) -> str:
        if shortcut_id in self._shortcuts:
            shortcut, _ = self._shortcuts[shortcut_id]
            return shortcut.get_display_string()

        return ""

    def add_menu_item(self, shortcut_id: ShortcutId, **kwargs: Any) -> None:
        shortcut, callback = self._shortcuts[shortcut_id]
        dpg.add_menu_item(
            callback=lambda s, a, u: callback(),
            shortcut=shortcut.get_display_string(),
            **kwargs,
        )

    def bind_all(self) -> None:
        with dpg.handler_registry() as self._handler_registry:
            for shortcut, callback in self._shortcuts.values():

                def handler(shortcut: Shortcut, callback: Callback) -> Callable[[Sender, Any, Any], None]:
                    def inner(sender: Sender, app_data: Any, user_data: Any) -> None:
                        self._handle_key(shortcut, callback)

                    return inner

                dpg.add_key_press_handler(
                    key=shortcut.key,
                    callback=handler(shortcut, callback),
                )

    def _handle_key(self, shortcut: Shortcut, callback: Callback) -> None:
        if self._enabled and self._modifiers_match(shortcut.modifiers):
            callback()

    @staticmethod
    def _modifiers_match(required: Tuple[Modifier, ...]) -> bool:
        ctrl_pressed = dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)
        shift_pressed = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)
        alt_pressed = dpg.is_key_down(dpg.mvKey_LAlt) or dpg.is_key_down(dpg.mvKey_RAlt)

        ctrl_required = Modifier.CTRL in required
        shift_required = Modifier.SHIFT in required
        alt_required = Modifier.ALT in required

        return all(
            (
                ctrl_pressed == ctrl_required,
                shift_pressed == shift_required,
                alt_pressed == alt_required,
            )
        )

    def setup_focus_handler(self) -> None:
        with dpg.item_handler_registry(tag=self._focus_handler_tag):
            dpg.add_item_activated_handler(callback=self._on_input_focused)
            dpg.add_item_deactivated_handler(callback=self._on_input_unfocused)
            dpg.add_item_deactivated_after_edit_handler(callback=self._on_input_unfocused)

    def setup_input_focus_handlers(self, input_tag: str) -> None:
        if dpg.does_item_exist(input_tag) and dpg.does_item_exist(self._focus_handler_tag):
            dpg.bind_item_handler_registry(input_tag, self._focus_handler_tag)

    def _on_input_focused(self, sender: Sender, app_data: Any) -> None:
        self.disable()

    def _on_input_unfocused(self, sender: Sender, app_data: Any) -> None:
        self.enable()
