from typing import Callable, Final

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.callback import Callback

CANCEL_FOCUS_STOP: Final[int] = 2


class GUISaveConfirmationWindow(GUIDialogWindow):
    """A modal save-or-proceed prompt for an unsaved document.

    ``on_save`` writes the document and reports whether it completed; the prompt runs
    ``on_confirm`` and closes once the save reports success, so a cancelled save keeps the
    prompt open for another attempt. The middle button discards the pending changes and
    runs ``on_confirm`` to proceed, and Cancel — the initially focused button — dismisses
    the prompt.
    """

    _fits_content = True

    def __init__(
        self,
        tag: str,
        *,
        width: int,
        height: int,
        wrap: int,
        save_label: str,
        cancel_label: str,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._wrap = wrap
        self._save_label = save_label
        self._cancel_label = cancel_label

        self._message: str
        self._title: str
        self._on_save: Callable[[], bool]
        self._on_confirm: Callback
        self._ok_label: str

        super().__init__(
            tag,
            width,
            height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def prepare(
        self,
        message: str,
        title: str,
        on_save: Callable[[], bool],
        on_confirm: Callback,
        *,
        ok_label: str,
    ) -> None:
        """Captures the pending document's write and the two ways forward."""
        self._message = message
        self._title = title
        self._on_save = on_save
        self._on_confirm = on_confirm
        self._ok_label = ok_label

    def create_window(self) -> None:
        save_button_tag = compose_tag(self.tag, SUF_BUTTON_SAVE)
        ok_button_tag = compose_tag(self.tag, SUF_BUTTON_OK)
        cancel_button_tag = compose_tag(self.tag, SUF_BUTTON_CANCEL)

        def disable() -> None:
            dpg_configure_item(save_button_tag, enabled=False)
            dpg_configure_item(ok_button_tag, enabled=False)
            dpg_configure_item(cancel_button_tag, enabled=False)

        def _on_save() -> None:
            if not self._on_save():
                return

            disable()
            self._on_confirm()
            self.hide()

        def _on_confirm() -> None:
            disable()
            self._on_confirm()
            self.hide()

        def _on_cancel() -> None:
            disable()
            self.hide()

        def content(parent: str) -> None:
            dpg.add_text(self._message, parent=parent, wrap=self._wrap)

            @table_wrapper(columns=3)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=save_button_tag,
                    label=self._save_label,
                    callback=_on_save,
                    width=-1,
                )
                GUIButton(
                    tag=ok_button_tag,
                    label=self._ok_label,
                    callback=_on_confirm,
                    width=-1,
                )
                GUIButton(
                    tag=cancel_button_tag,
                    label=self._cancel_label,
                    callback=_on_cancel,
                    width=-1,
                )

            buttons(None)

        with self.dialog_window(label=self._title, on_close=_on_cancel):
            content(self.tag)

        self._install_navigation(
            [
                FocusStop.button(save_button_tag, _on_save),
                FocusStop.button(ok_button_tag, _on_confirm),
                FocusStop.button(cancel_button_tag, _on_cancel),
            ],
            on_escape=_on_cancel,
            initial_index=CANCEL_FOCUS_STOP,
        )
