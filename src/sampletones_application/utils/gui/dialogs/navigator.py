from typing import List

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import SUF_HANDLER_DIALOG_NAV
from sampletones_application.utils.gui.dialogs.ring import FocusRing
from sampletones_application.utils.gui.dialogs.stop import FocusStop
from sampletones_application.utils.gui.dpg import dpg_delete_item
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.shortcuts.manager import ShortcutManager
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class DialogKeyboardNavigator:
    """Keyboard navigation for one modal dialog: Tab cycles its controls, Enter activates the
    focused button, Escape cancels.

    While the dialog is shown it holds :class:`ShortcutManager`'s modal claim, so every
    application key action stays behind the modal until it closes. Traversal is delegated to a
    :class:`FocusRing`; this class owns the key handler, the modal claim, and the mapping from
    key press to ring action.
    """

    def __init__(
        self,
        *,
        window_tag: str,
        stops: List[FocusStop],
        on_escape: VoidCallback,
        shortcut_manager: ShortcutManager,
        initial_index: int = 0,
    ) -> None:
        self._window_tag = window_tag
        self._ring = FocusRing(stops, initial_index)
        self._on_escape = on_escape
        self._shortcut_manager = shortcut_manager
        self._registry_tag = f"{window_tag}{SUF_HANDLER_DIALOG_NAV}"
        self._disposed = False

    def install(self) -> None:
        """Registers the key handler, claims the keyboard, and focuses the initial stop.

        A registry left over from a previous appearance of a fixed-tag window is cleared first,
        and the initial focus is deferred a frame so the freshly built tree is present.
        """
        dpg_delete_item(self._registry_tag)
        with dpg.handler_registry(tag=self._registry_tag):
            dpg.add_key_press_handler(callback=self._on_key)

        self._shortcut_manager.push_modal()
        FrameCallbackManager.set_frame_callback(self._focus_initial)

    def dispose(self) -> None:
        """Releases the keyboard claim and removes the key handler, once per navigator."""
        if self._disposed:
            return

        self._disposed = True
        self._shortcut_manager.pop_modal()
        dpg_delete_item(self._registry_tag)

    def _focus_initial(self) -> None:
        if dpg.does_item_exist(self._window_tag):
            self._ring.focus_initial()

    def _on_key(self, sender: Sender, app_data: int) -> None:
        if not dpg.does_item_exist(self._window_tag):
            self.dispose()
            return

        match app_data:
            case dpg.mvKey_Tab:
                backward = dpg.is_key_down(dpg.mvKey_LShift) or dpg.is_key_down(dpg.mvKey_RShift)
                self._ring.cycle(-1 if backward else 1)
            case dpg.mvKey_Return:
                self._ring.activate_focused()
            case dpg.mvKey_Escape:
                self._on_escape()
