from dataclasses import dataclass
from typing import Callable, Final, List, Protocol

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard import focus
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_shared.types.application import Sender

PRIORITY_MODAL: Final = 100
PRIORITY_PANEL: Final = 60
PRIORITY_SHORTCUT: Final = 40

KeyHandler = Callable[[KeyEvent], bool]
ActivePredicate = Callable[[], bool]


class ModalKeyHandler(Protocol):
    def handle_key(self, event: KeyEvent) -> None:
        """Acts on one key press while this handler's dialog holds the keyboard."""


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
        self._modal_stack: List[ModalKeyHandler] = []
        self._bound: bool = False
        self.register(
            self._route_modal,
            priority=PRIORITY_MODAL,
            active=lambda: self.is_modal_open,
        )

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
        self._scopes.append(
            _Scope(
                priority=priority,
                active=active,
                handle=handle,
            )
        )
        self._scopes.sort(key=lambda scope: scope.priority, reverse=True)

    @property
    def is_modal_open(self) -> bool:
        """Whether a modal dialog currently holds the keyboard."""
        return bool(self._modal_stack)

    @property
    def is_field_focused(self) -> bool:
        """Whether a text or value field is being edited and should keep plain keys for itself.

        The scopes consult this single flag, so a key press stays with the field the user is
        typing into and reaches shortcuts otherwise.
        """
        return focus.is_field_focused()

    def push_modal(self, handler: ModalKeyHandler) -> None:
        """Gives ``handler`` the keyboard as the active modal dialog.

        Stacking handlers keeps a dialog opened on top of another routing keys until it closes,
        when the dialog beneath it resumes ownership of the keyboard.
        """
        self._modal_stack.append(handler)

    def pop_modal(self) -> None:
        """Releases the top modal dialog's claim on the keyboard, ignored when none is open."""
        if self._modal_stack:
            self._modal_stack.pop()

    def route(self, event: KeyEvent) -> bool:
        """Offers the event to the active scopes, highest priority first, stopping at the
        first that claims it; returns whether any scope claimed it."""
        for scope in self._scopes:
            if scope.active() and scope.handle(event):
                return True

        return False

    def _route_modal(self, event: KeyEvent) -> bool:
        """Hands the key to the dialog on top of the modal stack and claims it.

        A modal dialog owns the keyboard while it is shown, so the press is kept from the panel
        and shortcut scopes and the active dialog alone decides what its navigation keys do.
        """
        self._modal_stack[-1].handle_key(event)
        return True

    def _dispatch(self, sender: Sender, app_data: int) -> None:
        self.route(KeyEvent.capture(app_data))
