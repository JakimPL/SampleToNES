from typing import Any, Dict, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard import (
    PRIORITY_SHORTCUT,
    KeyEvent,
    KeyRouter,
    focus,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    def __init__(self, *, key_router: KeyRouter) -> None:
        self._router = key_router
        self._shortcuts: Dict[ShortcutId, Tuple[Shortcut, Callback]] = {}
        self._bindings_by_key: Dict[int, List[Tuple[Shortcut, Callback]]] = {}

    def register(
        self,
        shortcut_id: ShortcutId,
        shortcut: Shortcut,
        callback: Callback,
    ) -> None:
        self._shortcuts[shortcut_id] = (shortcut, callback)

    def add_menu_item(self, shortcut_id: ShortcutId, **kwargs: Any) -> None:
        shortcut, callback = self._shortcuts[shortcut_id]
        dpg.add_menu_item(
            callback=lambda s, a, u: callback(),
            shortcut=shortcut.display(),
            **kwargs,
        )

    def bind_all(self) -> None:
        """Registers the shortcut scope with the key router.

        Bindings are indexed by key so a press resolves in one lookup. A modal dialog claims keys
        at a higher priority, so this scope handles a press whenever no dialog holds the keyboard.
        """
        self._bindings_by_key = {}
        for shortcut, callback in self._shortcuts.values():
            self._add_binding(shortcut, callback)

        self._router.register(
            self._dispatch,
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )

    def _add_binding(self, shortcut: Shortcut, callback: Callback) -> None:
        """Indexes the binding under each key any of its combinations names."""
        for key in sorted({combination.key for combination in shortcut.combinations()}):
            self._bindings_by_key.setdefault(key, []).append(
                (
                    shortcut,
                    callback,
                )
            )

    def _dispatch(self, event: KeyEvent) -> bool:
        """Fires the shortcut matching the event, yielding its key to a focused field that acts on
        it unless the shortcut is field-transparent.

        A field keeps only the keys it uses, so a text field holds plain Space and its editing keys
        while Ctrl+Space and Escape still reach playback and Stop from the same field.
        """
        for shortcut, callback in self._bindings_by_key.get(event.key, ()):
            if not shortcut.matches(event):
                continue

            if not shortcut.field_transparent and self._field_consumes(event):
                return False

            callback()
            return True

        return False

    @staticmethod
    def _field_consumes(event: KeyEvent) -> bool:
        return focus.field_consumes_key(
            focus.focused_field_kind(),
            event.key,
            event.modifiers,
        )
