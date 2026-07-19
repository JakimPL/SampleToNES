from typing import Any, Dict, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard import PRIORITY_SHORTCUT, KeyEvent, KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.keys import Modifier
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    def __init__(self, *, key_router: KeyRouter) -> None:
        self._router = key_router
        self._shortcuts: Dict[ShortcutId, Tuple[Shortcut, Callback]] = {}
        self._aliases: Dict[ShortcutId, List[Shortcut]] = {}
        self._bindings_by_key: Dict[int, List[Tuple[Shortcut, Callback]]] = {}

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
        """Whether a text or value field currently owns keyboard focus.

        The key router reads focus at the source each key press, so both shortcut dispatch and the
        sequencer key handlers consult this to keep typed characters with the field they belong to.
        """
        return self._router.is_field_focused

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

        Bindings are indexed by key so a press resolves in one lookup. A modal dialog claims keys
        at a higher priority, so this scope handles a press whenever no dialog holds the keyboard.
        """
        self._bindings_by_key = {}
        for shortcut_id, (shortcut, callback) in self._shortcuts.items():
            self._add_binding(shortcut, callback)
            for alias in self._aliases.get(shortcut_id, []):
                self._add_binding(alias, callback)

        self._router.register(
            self._dispatch,
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
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
