from typing import Callable, Final

import dearpygui.dearpygui as dpg

from sampletones_application.layout.primitives import DialogGeometry
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
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.callback import Callback

CANCEL_FOCUS_STOP: Final[int] = 2


class GUISaveConfirmationWindow(GUIDialogWindow):
    """A modal save-or-proceed prompt for an unsaved document.

    Every answer runs a frame after the prompt has left the screen, so whatever it opens stands
    alone. Save runs ``on_save``, which reports a :class:`SaveOutcome`: a written document runs
    ``on_confirm``, a save the reader called off brings the prompt back with the same question,
    and a failed save leaves its error on screen by itself and runs ``on_cancel``. The middle
    button discards the pending changes and runs ``on_confirm`` to proceed. Cancel, the initially
    focused button, runs ``on_cancel``, and so do Escape and the title bar's close button, so every
    way out of the prompt reaches the caller.
    """

    def __init__(
        self,
        tag: str,
        *,
        geometry: DialogGeometry,
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
        self._on_save: Callable[[], SaveOutcome]
        self._on_confirm: Callback
        self._on_cancel: Callback
        self._ok_label: str

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
        on_save: Callable[[], SaveOutcome],
        on_confirm: Callback,
        on_cancel: Callback,
        *,
        ok_label: str,
    ) -> None:
        """Captures the pending document's write, the two ways forward and the way back."""
        self._message = message
        self._title = title
        self._on_save = on_save
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel
        self._ok_label = ok_label

    def create_window(self) -> None:
        save_button_tag = compose_tag(self.tag, SUF_BUTTON_SAVE)
        ok_button_tag = compose_tag(self.tag, SUF_BUTTON_OK)
        cancel_button_tag = compose_tag(self.tag, SUF_BUTTON_CANCEL)

        def _on_save() -> None:
            self._leave_then(self._save_and_go_on)

        def _on_confirm() -> None:
            self._leave_then(self._on_confirm)

        def _on_cancel() -> None:
            self._leave_then(self._on_cancel)

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

    def _save_and_go_on(self) -> None:
        """Writes the document and goes where the outcome leads, once the prompt has left.

        A written document goes on to what the prompt was guarding. A save the reader called off
        puts the same question again. A failed save showed its error, which stands alone, and the
        request the prompt guarded goes back the way Cancel takes it. A save that raises turns the
        request back the same way, and its error goes on up.
        """
        match self._saved():
            case SaveOutcome.WRITTEN:
                self._on_confirm()
            case SaveOutcome.CALLED_OFF:
                self.show(
                    self._message,
                    self._title,
                    self._on_save,
                    self._on_confirm,
                    self._on_cancel,
                    ok_label=self._ok_label,
                )
            case SaveOutcome.FAILED:
                self._on_cancel()

    def _saved(self) -> SaveOutcome:
        """What the save came to, with the request the prompt guarded turned back where the save raises."""
        reported = False
        try:
            outcome = self._on_save()
            reported = True
        finally:
            if not reported:
                self._on_cancel()

        return outcome
