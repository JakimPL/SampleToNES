from pathlib import Path
from typing import Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_CHECKBOX,
    SUF_PATH,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.ui.elements.path import GUIPathText
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_shared.types.callback import Callback, VoidCallback

CANCEL_FOCUS_STOP: Final[int] = 1


class GUIConfirmationWindow(GUIDialogWindow):
    """A modal asking one question, answered through OK, Cancel, Escape, or the title-bar close.

    ``on_confirm``/``on_cancel`` run on the respective choice, and the title bar and Escape
    read as the negative one, so every way out of the prompt reaches the caller. Each answer
    runs a frame after the prompt has left the screen, so a question the answer asks next
    opens alone. A checked opt-out checkbox adds ``on_opt_out`` to a confirmation, letting
    the caller suppress future prompts; the box is read as the prompt leaves. Cancel — the
    initially focused button — keeps the prompt answerable by keyboard alone.
    """

    def __init__(
        self,
        tag: str,
        *,
        geometry: DialogGeometry,
        wrap: int,
        path_color: BaseColor,
        path_hover_color: BaseColor,
        path_message: str,
        status_bar: GUIStatusBar,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._wrap = wrap
        self._path_color = path_color
        self._path_hover_color = path_hover_color
        self._path_message = path_message
        self._status_bar = status_bar

        self._message: str
        self._title: str
        self._on_confirm: Callback
        self._on_cancel: Optional[Callback]
        self._on_opt_out: Optional[Callback]
        self._ok_label: str
        self._cancel_label: str
        self._path: Optional[Path]
        self._opt_out_label: Optional[str]

        super().__init__(
            tag,
            geometry,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def prepare(  # pylint: disable=arguments-differ
        self,
        message: str,
        title: str,
        on_confirm: Callback,
        *,
        ok_label: str,
        cancel_label: str,
        path: Optional[Path],
        opt_out_label: Optional[str],
        on_opt_out: Optional[Callback],
        on_cancel: Optional[Callback],
    ) -> None:
        """Captures the question and its answers for the next appearance."""
        self._message = message
        self._title = title
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._on_opt_out = on_opt_out
        self._ok_label = ok_label
        self._cancel_label = cancel_label
        self._path = path
        self._opt_out_label = opt_out_label

    def create_window(self) -> None:
        opt_out_tag = compose_tag(self.tag, SUF_CHECKBOX)
        ok_button_tag = compose_tag(self.tag, SUF_BUTTON_OK)
        cancel_button_tag = compose_tag(self.tag, SUF_BUTTON_CANCEL)

        def _on_confirm() -> None:
            self._leave_then(self._confirmation(opted_out=self._is_opted_out(opt_out_tag)))

        def _on_cancel() -> None:
            if self._on_cancel is None:
                self.hide()
                return

            self._leave_then(self._on_cancel)

        def content(parent: str) -> None:
            dpg.add_text(self._message, parent=parent, wrap=self._wrap)

            if self._path is not None:
                GUIPathText(
                    tag=compose_tag(self.tag, SUF_PATH),
                    path=self._path,
                    parent=parent,
                    color=self._path_color,
                    hover_color=self._path_hover_color,
                    status_message=self._path_message,
                    use_filename_only=True,
                    status_bar=self._status_bar,
                )

            if self._opt_out_label is not None:
                dpg.add_checkbox(
                    label=self._opt_out_label,
                    tag=opt_out_tag,
                    parent=parent,
                )

            @table_wrapper(columns=2)
            def buttons(_: None) -> None:
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
                FocusStop.button(ok_button_tag, _on_confirm),
                FocusStop.button(cancel_button_tag, _on_cancel),
            ],
            on_escape=_on_cancel,
            initial_index=CANCEL_FOCUS_STOP,
        )

    def _is_opted_out(self, opt_out_tag: str) -> bool:
        """Whether the reader ticked the opt-out box, read while the prompt still stands."""
        return self._opt_out_label is not None and dpg.does_item_exist(opt_out_tag) and bool(dpg.get_value(opt_out_tag))

    def _confirmation(self, *, opted_out: bool) -> VoidCallback:
        """The confirmation this appearance answers with, the opt-out riding it when it was ticked."""
        on_confirm = self._on_confirm
        on_opt_out = self._on_opt_out if opted_out else None

        def confirm() -> None:
            if on_opt_out is not None:
                on_opt_out()

            on_confirm()

        return confirm
