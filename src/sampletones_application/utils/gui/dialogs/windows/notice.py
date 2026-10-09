from typing import Any

import dearpygui.dearpygui as dpg

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON_OK
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.callback import StringCallback


class GUINoticeWindow(GUIDialogWindow):
    """A dialog stating something the reader acknowledges, with one button to dismiss it.

    What the notice says is drawn by the caller into the window's own tag, so a message, a
    path or a list of settings all reach the reader through one dialog. A notice claiming
    the screen answers to Tab, Enter and Escape; one reporting something already done stands
    beside an interface that stays live, where the keys keep reaching what the reader was
    working in and the button is clicked.
    """

    def __init__(
        self,
        tag: str,
        *,
        geometry: DialogGeometry,
        title: str,
        content: StringCallback,
        ok_label: str,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
        claims_the_screen: bool,
    ) -> None:
        self._title = title
        self._content = content
        self._ok_label = ok_label
        self._claims_the_screen = claims_the_screen

        super().__init__(
            tag,
            geometry,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """What the notice says was named when it was built."""

    def create_window(self) -> None:
        ok_button_tag = compose_tag(self.tag, SUF_BUTTON_OK)
        with self.dialog_window(label=self._title, on_close=self.hide):
            self._content(self.tag)
            dpg.add_separator(parent=self.tag)
            GUIButton(
                tag=ok_button_tag,
                label=self._ok_label,
                callback=self.hide,
                parent=self.tag,
                width=-1,
            )

        if self._claims_the_screen:
            self._install_navigation(
                [FocusStop.button(ok_button_tag, self.hide)],
                on_escape=self.hide,
            )


def show_notice(
    tag: str,
    title: str,
    content: StringCallback,
    *,
    geometry: DialogGeometry,
    ok_label: str,
    key_router: KeyRouter,
    shortcut_source: ShortcutSource,
    claims_the_screen: bool = True,
) -> None:
    """Raises one notice the reader acknowledges, drawn at the size ``geometry`` states."""
    GUINoticeWindow(
        tag=tag,
        geometry=geometry,
        title=title,
        content=content,
        ok_label=ok_label,
        key_router=key_router,
        shortcut_source=shortcut_source,
        claims_the_screen=claims_the_screen,
    ).show()
