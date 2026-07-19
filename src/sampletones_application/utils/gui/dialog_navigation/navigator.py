from typing import List

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.dialog_navigation.ring import FocusRing
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_shared.types.callback import VoidCallback


class DialogKeyboardNavigator:
    """Keyboard navigation for one modal dialog: Tab cycles its controls, Enter activates the
    focused button, Escape cancels.

    While the dialog is shown it holds the key router's modal claim, so the router sends every key
    press here and keeps them from the panel and shortcut scopes until the dialog closes. Traversal
    is delegated to a :class:`FocusRing`; this class owns the modal claim and the mapping from key
    press to ring action.
    """

    def __init__(
        self,
        *,
        window_tag: str,
        stops: List[FocusStop],
        on_escape: VoidCallback,
        key_router: KeyRouter,
        initial_index: int = 0,
    ) -> None:
        self._window_tag = window_tag
        self._ring = FocusRing(stops, initial_index)
        self._on_escape = on_escape
        self._router = key_router
        self._disposed = False

    def install(self) -> None:
        """Claims the keyboard for this dialog and focuses its initial stop.

        The initial focus is deferred a frame so the freshly built tree is present.
        """
        self._router.push_modal(self)
        FrameCallbackManager.set_frame_callback(self._focus_initial)

    def dispose(self) -> None:
        """Releases the keyboard claim, once per navigator."""
        if self._disposed:
            return

        self._disposed = True
        self._router.pop_modal()

    def _focus_initial(self) -> None:
        if dpg.does_item_exist(self._window_tag):
            self._ring.focus_initial()

    def handle_key(self, event: KeyEvent) -> None:
        """Routes Tab/Enter/Escape to the focus ring, disposing once the dialog has vanished."""
        if not dpg.does_item_exist(self._window_tag):
            self.dispose()
            return

        match event.key:
            case dpg.mvKey_Tab:
                self._ring.cycle(-1 if event.shift else 1)
            case dpg.mvKey_Return:
                self._ring.activate_focused()
            case dpg.mvKey_Escape:
                self._on_escape()
