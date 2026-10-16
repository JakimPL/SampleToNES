from dataclasses import dataclass
from typing import Callable, Dict, Final, List, Optional, Protocol

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.keyboard import focus
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_shared.types.application import Sender

PRIORITY_MODAL: Final = 100
PRIORITY_PANEL: Final = 60
PRIORITY_SHORTCUT: Final = 40

KeyHandler = Callable[[KeyEvent], bool]
KeyReleaseHandler = Callable[[int], None]
ActivePredicate = Callable[[], bool]


class ModalKeyHandler(Protocol):
    def handle_key(self, event: KeyEvent) -> None:
        """Acts on one key press while this handler's dialog holds the keyboard."""


@dataclass(frozen=True)
class _Scope:
    priority: int
    active: ActivePredicate
    handle: KeyHandler
    release: Optional[KeyReleaseHandler]


class KeyRouter:
    """The single owner of the application's global key-press and key-release handlers.

    Every keyboard consumer registers a scope with a priority and an ``active`` predicate.
    On each key press the router snapshots the modifiers and offers the event to the active
    scopes from highest priority to lowest, stopping at the first that claims it. This gives
    the priority and consume semantics DearPyGui itself lacks: its key handlers are all
    global, and none can stop another — or ImGui — from also seeing the key.

    A scope that holds its keys, as a key sounding a note for as long as it is down, takes the
    release of every press it claimed, whichever scope is active when the key comes up, so a tab
    switch or a dialog opening while the key is down leaves nothing held. DearPyGui repeats a
    press for as long as its key is down, so a held key's repeats reach no scope. A key whose
    release the window missed, as when the window loses focus while it is down, is released by
    the sweep of the frame that finds it up.
    """

    def __init__(self) -> None:
        self._scopes: List[_Scope] = []
        self._modal_stack: List[ModalKeyHandler] = []
        self._held: Dict[int, _Scope] = {}
        self._bound: bool = False
        self.register(
            self._route_modal,
            priority=PRIORITY_MODAL,
            active=lambda: self.is_modal_open,
        )

    def bind(self) -> None:
        """Installs the one global key-press handler and the one key-release handler, once the context exists."""
        if self._bound:
            return

        self._bound = True
        with dpg.handler_registry():
            dpg.add_key_press_handler(callback=self._dispatch)
            dpg.add_key_release_handler(callback=self._dispatch_release)

    def register(
        self,
        handle: KeyHandler,
        *,
        priority: int,
        active: ActivePredicate,
    ) -> None:
        """Adds a scope, keeping the scopes ordered from highest priority to lowest."""
        self._add(
            _Scope(
                priority=priority,
                active=active,
                handle=handle,
                release=None,
            )
        )

    def register_holding(
        self,
        handle: KeyHandler,
        release: KeyReleaseHandler,
        *,
        priority: int,
        active: ActivePredicate,
    ) -> None:
        """Adds a scope holding the keys it claims until they come up, which takes their releases."""
        self._add(
            _Scope(
                priority=priority,
                active=active,
                handle=handle,
                release=release,
            )
        )

    def _add(self, scope: _Scope) -> None:
        self._scopes.append(scope)
        self._scopes.sort(key=lambda standing: standing.priority, reverse=True)

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

    def pop_modal(self, handler: ModalKeyHandler) -> None:
        """Releases the latest claim ``handler`` holds on the keyboard, wherever it stands.

        A dialog can close while one it raised still stands, so a release names whose claim it
        gives up and every other claim keeps its place. A handler holding no claim changes nothing.
        """
        for index in range(len(self._modal_stack) - 1, -1, -1):
            if self._modal_stack[index] is handler:
                del self._modal_stack[index]
                return

    def route(self, event: KeyEvent) -> bool:
        """Offers the event to the active scopes, highest priority first, stopping at the
        first that claims it; returns whether any scope claimed it.

        A press repeating a key a scope holds is claimed for that scope and reaches none.
        """
        if event.key in self._held:
            return True

        for scope in self._scopes:
            if scope.active() and scope.handle(event):
                if scope.release is not None:
                    self._held[event.key] = scope

                return True

        return False

    def release(self, key: int) -> None:
        """Hands the release of ``key`` to the scope holding it, where one does."""
        scope = self._held.pop(key, None)
        if scope is not None and scope.release is not None:
            scope.release(key)

    def sweep(self) -> None:
        """Releases every held key the window no longer reports down, once a frame."""
        for key in [key for key in self._held if not dpg.is_key_down(key)]:
            self.release(key)

    def _route_modal(self, event: KeyEvent) -> bool:
        """Hands the key to the dialog on top of the modal stack and claims it.

        A modal dialog owns the keyboard while it is shown, so the press is kept from the panel
        and shortcut scopes and the active dialog alone decides what its navigation keys do.
        """
        self._modal_stack[-1].handle_key(event)
        return True

    def _dispatch(self, _sender: Sender, app_data: int) -> None:
        self.route(KeyEvent.capture(app_data))

    def _dispatch_release(self, _sender: Sender, app_data: int) -> None:
        self.release(app_data)
