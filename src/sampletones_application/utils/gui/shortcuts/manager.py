from typing import Any, Dict, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.keyboard import (
    PRIORITY_SHORTCUT,
    KeyEvent,
    KeyRouter,
    focus,
)
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import Callback


class ShortcutManager:
    """Dispatches a key press to the action it fires, reading each action's keys from the scheme.

    An action is registered under the id it answers to together with the call it makes; which
    combination reaches it is the keybinding scheme's to say, so a rebind changes the keys without
    touching a registration.
    """

    def __init__(
        self,
        *,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._router = key_router
        self._source = shortcut_source
        self._callbacks: Dict[ShortcutId, Callback] = {}
        self._bindings_by_key: Dict[int, List[Tuple[Shortcut, Callback]]] = {}
        self._menu_items: Dict[Sender, ShortcutId] = {}

    def register(self, shortcut_id: ShortcutId, callback: Callback) -> None:
        """Names the call an action makes when its combination is pressed or its menu item chosen."""
        self._callbacks[shortcut_id] = callback

    def add_menu_item(self, shortcut_id: ShortcutId, **kwargs: Any) -> None:
        """Adds the menu item an action is chosen from, printing the combination that also fires it.

        The item is kept under the action it stands for, so a later rebind reaches the accelerator
        already on screen.
        """
        callback = self._callbacks[shortcut_id]
        item: Sender = dpg.add_menu_item(
            callback=lambda s, a, u: callback(),
            shortcut=self._source.display(shortcut_id),
            **kwargs,
        )
        self._menu_items[item] = shortcut_id

    def bind_all(self) -> None:
        """Registers the shortcut scope with the key router.

        Bindings are indexed by key so a press resolves in one lookup. A modal dialog claims keys
        at a higher priority, so this scope handles a press whenever no dialog holds the keyboard.
        The scope is claimed the once here, which leaves a rebind to re-read the keys in place.
        """
        self._index_bindings()
        self._router.register(
            self._dispatch,
            priority=PRIORITY_SHORTCUT,
            active=lambda: True,
        )

    def rebind(self) -> None:
        """Reads every action's keys again, once another scheme is the one in place.

        A registration names the action it fires, so a rebind catches up the copies of the keys:
        the index a press resolves through and the accelerators already on screen.
        """
        self._index_bindings()
        self._refresh_menu_items()

    def _refresh_menu_items(self) -> None:
        """Prints each menu item's accelerator again, so a menu shows the keys that reach it."""
        for item, shortcut_id in self._menu_items.items():
            dpg_configure_item(item, shortcut=self._source.display(shortcut_id))

    def _index_bindings(self) -> None:
        """Reads each registered action's combinations from the scheme and indexes them by key."""
        self._bindings_by_key = {}
        for shortcut_id, callback in self._callbacks.items():
            self._add_binding(self._source.shortcut(shortcut_id), callback)

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
