from typing import Any, Dict, List, Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_HANDLER_FOCUS
from sampletones_application.utils.gui.keyboard import PRIORITY_SHORTCUT, KeyEvent, KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    def __init__(self, *, key_router: KeyRouter) -> None:
        self._router = key_router
        self._shortcuts: Dict[ShortcutId, Tuple[Shortcut, Callback]] = {}
        self._aliases: Dict[ShortcutId, List[Shortcut]] = {}
        self._bindings_by_key: Dict[int, List[Tuple[Shortcut, Callback]]] = {}
        self._focused_input: Optional[Sender] = None

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
        action behind the modal until it closes. The claim itself lives on the key router.
        """
        return self._router.is_modal_open

    def push_modal(self) -> None:
        """Registers that a modal dialog has taken over the keyboard."""
        self._router.push_modal()

    def pop_modal(self) -> None:
        """Releases one modal dialog's claim on the keyboard."""
        self._router.pop_modal()

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
        """Registers the shortcut scope with the key router.

        Bindings are indexed by key so a press resolves in one lookup; the router skips this
        scope entirely while a modal dialog holds the keyboard.
        """
        self._bindings_by_key = {}
        for shortcut_id, (shortcut, callback) in self._shortcuts.items():
            self._add_binding(shortcut, callback)
            for alias in self._aliases.get(shortcut_id, []):
                self._add_binding(alias, callback)

        self._router.register(
            self._dispatch,
            priority=PRIORITY_SHORTCUT,
            active=lambda: not self._router.is_modal_open,
        )

    def _add_binding(self, shortcut: Shortcut, callback: Callback) -> None:
        if shortcut.key is None:
            return

        self._bindings_by_key.setdefault(shortcut.key, []).append((shortcut, callback))

    def _dispatch(self, event: KeyEvent) -> bool:
        """Fires the shortcut matching the event, leaving its key to a focused field
        unless the shortcut is field-transparent."""
        for shortcut, callback in self._bindings_by_key.get(event.key, ()):
            if self._modifiers_match(event, shortcut.modifiers):
                if self.is_input_focused and not shortcut.field_transparent:
                    return False

                callback()
                return True

        return False

    @staticmethod
    def _modifiers_match(event: KeyEvent, required: Tuple[Modifier, ...]) -> bool:
        return (
            event.ctrl == (Modifier.CTRL in required)
            and event.shift == (Modifier.SHIFT in required)
            and event.alt == (Modifier.ALT in required)
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
