from typing import Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON_OK,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_GROUP,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.ui.elements.trace import GUITraceback
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.palette.dpg import dpg_set_palette_color
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.utils.palette.colors.base import BaseColor

OK_FOCUS_STOP: Final[int] = 1


class GUIErrorDialogWindow(GUIDialogWindow):
    """A modal reporting an exception with its message and an optional traceback.

    The exception's name and text are drawn in the error colour, the traceback starts
    hidden behind its toggle, and OK — the initially focused button — dismisses the
    prompt. The title-bar close reads the same way.
    """

    def __init__(
        self,
        tag: str,
        *,
        width: int,
        height: int,
        wrap: int,
        language_manager: LanguageManager,
        error_color: BaseColor,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._language_manager = language_manager
        self._wrap = wrap
        self._error_color = error_color
        self._exception: Exception
        self._message: Optional[str]

        super().__init__(
            tag,
            width,
            height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def prepare(self, exception: Exception, message: Optional[str]) -> None:
        """Captures the failure the next appearance reports."""
        self._exception = exception
        self._message = message

    def create_window(self) -> None:
        show_button_tag = compose_tag(self.tag, SUF_BUTTON_SHOW_TRACEBACK)
        ok_button_tag = compose_tag(self.tag, SUF_BUTTON_OK)
        traceback: GUITraceback

        with dpg.window(
            tag=self.tag,
            label=self._language_manager["global.dialog.title.error"],
            modal=True,
            min_size=(self.width, self.height),
            autosize=True,
            no_scrollbar=False,
            on_close=self.hide,
        ):
            if self._message is not None:
                dpg.add_text(self._message, parent=self.tag, wrap=self._wrap)

            group_tag = compose_tag(self.tag, SUF_GROUP)
            with dpg.group(tag=group_tag, parent=self.tag):
                name_text = dpg.add_text(
                    f"{type(self._exception).__name__!s}: ",
                    parent=group_tag,
                )
                dpg_set_palette_color(name_text, self._error_color)
                message_text = dpg.add_text(
                    str(self._exception),
                    parent=group_tag,
                    wrap=self._wrap,
                )
                dpg_set_palette_color(message_text, self._error_color)

            traceback = GUITraceback(
                parent=self.tag,
                exception=self._exception,
                language_manager=self._language_manager,
            )

            def toggle_traceback() -> None:
                traceback.toggle_visibility()
                dpg_configure_item(
                    show_button_tag,
                    label=(
                        self._language_manager["global.traceback.label.show"]
                        if not traceback.visible
                        else self._language_manager["global.traceback.label.hide"]
                    ),
                )

            dpg.add_separator()

            @table_wrapper(columns=2)
            def buttons(_: None) -> None:
                GUIButton(
                    tag=show_button_tag,
                    label=self._language_manager["global.traceback.label.show"],
                    width=-1,
                    callback=toggle_traceback,
                )
                GUIButton(
                    tag=ok_button_tag,
                    label=self._language_manager["global.dialog.label.ok"],
                    callback=self.hide,
                    width=-1,
                )

            buttons(None)

        self._install_navigation(
            [
                FocusStop.button(show_button_tag, toggle_traceback),
                FocusStop.button(ok_button_tag, self.hide),
            ],
            on_escape=self.hide,
            initial_index=OK_FOCUS_STOP,
        )
