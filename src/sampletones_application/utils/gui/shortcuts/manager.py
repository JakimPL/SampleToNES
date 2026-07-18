from typing import Any, Dict, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_HANDLER_FOCUS
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    def __init__(self) -> None:
        self._shortcuts: Dict[ShortcutId, Tuple[Shortcut, Callback]] = {}
        self._aliases: Dict[ShortcutId, List[Shortcut]] = {}
        self._focused_input: Optional[Sender] = None
        self._modal_depth: int = 0

        self._handler_registry: Optional[int] = None
        self._focus_handler_tag = TAG_GLOBAL_HANDLER_FOCUS

    def register(
        self,
        shortcut_id: ShortcutId,
        shortcut: Shortcut,
        callback: Callback,
    ) -> None:
        self._shortcuts[shortcut_id] = (shortcut, callback)

    def register_alias(self, shortcut_id: ShortcutId, shortcut: Shortcut) -> None:
        """Binds an additional key combination to an already registered action.

        The primary shortcut keeps the action's display string in menus and
        tooltips; an alias extends only the key handling, so one action honours
        several conventional combinations.
        """
        self._aliases.setdefault(shortcut_id, []).append(shortcut)

    @property
    def is_input_focused(self) -> bool:
        """Whether a text or numeric input currently owns keyboard focus.

        Registered inputs report focus through the shared focus handler, so both shortcut
        dispatch and the sequencer key handlers consult this to keep typed characters from
        reaching the tracker tables.
        """
        return self._focused_input is not None

    @property
    def is_dialog_open(self) -> bool:
        """Whether a modal dialog currently owns keyboard input.

        A dialog claims the keyboard for its own navigation while it is shown, so shortcut
        dispatch and the sequencer key handlers consult this to hold every application key
        action behind the modal until it closes.
        """
        return self._modal_depth > 0

    def push_modal(self) -> None:
        """Registers that a modal dialog has taken over the keyboard.

        Counting depth keeps a dialog opened on top of another dialog from releasing the
        keyboard until the last one closes.
        """
        self._modal_depth += 1

    def pop_modal(self) -> None:
        """Releases one modal dialog's claim on the keyboard, floored at zero."""
        self._modal_depth = max(0, self._modal_depth - 1)

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
            for shortcut_id, (shortcut, callback) in self._shortcuts.items():
                self._bind(shortcut, callback)
                for alias in self._aliases.get(shortcut_id, []):
                    self._bind(alias, callback)

    def _bind(self, shortcut: Shortcut, callback: Callback) -> None:
        if not shortcut.is_bindable:
            return

        def inner(sender: Sender, app_data: Any, user_data: Any) -> None:
            self._handle_key(shortcut, callback)

        dpg.add_key_press_handler(
            key=shortcut.key,
            callback=inner,
        )

    def _handle_key(self, shortcut: Shortcut, callback: Callback) -> None:
        if self.is_dialog_open:
            return

        if not self.is_input_focused and self._modifiers_match(shortcut.modifiers):
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

    def attach_focus_tracking(self, registry_tag: str) -> None:
        """Adds focus tracking to an item handler registry the input already binds.

        Inputs that carry their own registry (a commit or rename handler) bind one
        registry each, so their focus reporting is added into that same registry rather
        than the shared focus registry.
        """
        dpg.add_item_activated_handler(parent=registry_tag, callback=self._on_input_focused)
        dpg.add_item_deactivated_handler(parent=registry_tag, callback=self._on_input_unfocused)
        dpg.add_item_deactivated_after_edit_handler(parent=registry_tag, callback=self._on_input_unfocused)

    def _on_input_focused(self, sender: Sender, app_data: Sender) -> None:
        self._focused_input = app_data

    def _on_input_unfocused(self, sender: Sender, app_data: Sender) -> None:
        if self._focused_input == app_data:
            self._focused_input = None
