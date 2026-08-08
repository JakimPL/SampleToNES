from typing import Any, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.layout.primitives import Dimensions
from sampletones_application.tags.settings import (
    TAG_SETTINGS_DISPLAY_BUTTON_KEEP,
    TAG_SETTINGS_DISPLAY_BUTTON_REVERT,
    TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN,
    TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.dpg import dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_shared.types.callback import VoidCallback


class GUICountdownWindow(GUIWindow):
    """A modal asking to keep a change on screen, counting down while it waits.

    A change that can leave the window unreadable is confirmed here: whoever can still read the
    prompt keeps it, and the count reaching zero speaks for whoever cannot. The window shows the
    seconds its owner reports and reports both answers back; the owner runs the clock and decides
    what each answer means.

    Stacking over the dialog that armed it keeps that dialog on screen, so the change is judged
    against the window it was made in.
    """

    def __init__(
        self,
        *,
        layout: Dimensions,
        title: str,
        message: str,
        remaining_format: str,
        keep_label: str,
        revert_label: str,
        key_router: KeyRouter,
    ) -> None:
        self._title = title
        self._message = message
        self._remaining_format = remaining_format
        self._keep_label = keep_label
        self._revert_label = revert_label
        self._router = key_router
        self._navigator: Optional[DialogKeyboardNavigator] = None
        self._remaining = 0

        self.on_keep: Optional[VoidCallback] = None
        self.on_revert: Optional[VoidCallback] = None

        super().__init__(
            tag=TAG_SETTINGS_DISPLAY_WINDOW_COUNTDOWN,
            width=layout.width,
            height=layout.height,
        )

    def open(self, remaining: int) -> None:
        """Shows the prompt with the given number of seconds left to answer in."""
        self._remaining = remaining
        self.show()

    def set_remaining(self, remaining: int) -> None:
        """Shows the seconds left, repainting only when the count reaches a new second."""
        if remaining == self._remaining:
            return

        self._remaining = remaining
        dpg_set_value(TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN, self._remaining_text())

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The seconds left are seeded by :meth:`open` before the tree rebuilds."""

    def create_window(self) -> None:
        with self.dialog_window(
            label=self._title,
            on_close=None,
        ):
            dpg.add_text(self._message, wrap=self.width)
            dpg.add_text(self._remaining_text(), tag=TAG_SETTINGS_DISPLAY_TEXT_COUNTDOWN)
            dpg.add_separator()
            self._create_action_buttons()

        self._install_navigation()

    def _remaining_text(self) -> str:
        return self._remaining_format.format(seconds=self._remaining)

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_SETTINGS_DISPLAY_BUTTON_REVERT,
            label=self._revert_label,
            callback=self._revert,
            width=-1,
        )
        GUIButton(
            tag=TAG_SETTINGS_DISPLAY_BUTTON_KEEP,
            label=self._keep_label,
            callback=self._keep,
            width=-1,
        )

    def _install_navigation(self) -> None:
        """Wires Tab/Enter/Escape over the two answers, with Escape reading as reverting."""
        self._navigator = DialogKeyboardNavigator(
            window_tag=self.tag,
            stops=[
                FocusStop.button(TAG_SETTINGS_DISPLAY_BUTTON_REVERT, self._revert),
                FocusStop.button(TAG_SETTINGS_DISPLAY_BUTTON_KEEP, self._keep),
            ],
            on_escape=self._revert,
            key_router=self._router,
            initial_index=1,
        )
        self._navigator.install()

    def _teardown(self) -> None:
        if self._navigator is not None:
            self._navigator.dispose()
            self._navigator = None

    def _keep(self) -> None:
        self.call(self.on_keep)

    def _revert(self) -> None:
        self.call(self.on_revert)
