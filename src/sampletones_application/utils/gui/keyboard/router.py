from dataclasses import dataclass
from typing import Callable, Final, List

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard import focus
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_shared.types.application import Sender

PRIORITY_MODAL: Final = 100
PRIORITY_PANEL: Final = 60
PRIORITY_SHORTCUT: Final = 40

KeyHandler = Callable[[KeyEvent], bool]
ActivePredicate = Callable[[], bool]


@dataclass(frozen=True)
class _Scope:
    priority: int
    active: ActivePredicate
    handle: KeyHandler


class KeyRouter:
    """The single owner of the application's global key-press handler.

    Every keyboard consumer registers a scope with a priority and an ``active`` predicate.
    On each key press the router snapshots the modifiers and offers the event to the active
    scopes from highest priority to lowest, stopping at the first that claims it. This gives
    the priority and consume semantics DearPyGui itself lacks: its key handlers are all
    global, and none can stop another — or ImGui — from also seeing the key.
    """

    def __init__(self) -> None:
        self._scopes: List[_Scope] = []
        self._modal_depth: int = 0
        self._bound: bool = False

    def bind(self) -> None:
        """Installs the one global key-press handler, once, after the context exists."""
        if self._bound:
            return

        self._bound = True
        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self._dispatch)

    def register(
        self,
        handle: KeyHandler,
        *,
        priority: int,
        active: ActivePredicate,
    ) -> None:
        """Adds a scope, keeping the scopes ordered from highest priority to lowest."""
        self._scopes.append(_Scope(priority=priority, active=active, handle=handle))
        self._scopes.sort(key=lambda scope: scope.priority, reverse=True)

    @property
    def is_modal_open(self) -> bool:
        """Whether a modal dialog currently holds the keyboard."""
        return self._modal_depth > 0

    @property
    def is_field_focused(self) -> bool:
        """Whether a text or value field is being edited and should keep plain keys for itself.

        The scopes consult this one flag instead of each input reporting its own focus, so a key
        press stays with the field the user is typing into and reaches shortcuts otherwise.
        """
        return focus.is_field_focused()

    def push_modal(self) -> None:
        """Registers that a modal dialog has taken over the keyboard.

        Counting depth keeps a dialog opened on top of another from releasing the keyboard
        until the last one closes.
        """
        self._modal_depth += 1

    def pop_modal(self) -> None:
        """Releases one modal dialog's claim on the keyboard, floored at zero."""
        self._modal_depth = max(0, self._modal_depth - 1)

    def route(self, event: KeyEvent) -> bool:
        """Offers the event to the active scopes, highest priority first, stopping at the
        first that claims it; returns whether any scope claimed it."""
        for scope in self._scopes:
            if scope.active() and scope.handle(event):
                return True

        return False

    def _dispatch(self, sender: Sender, app_data: int) -> None:
        self.route(KeyEvent.capture(app_data))
