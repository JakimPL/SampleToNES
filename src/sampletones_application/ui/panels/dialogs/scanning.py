from pathlib import Path
from typing import Any, Final, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.general import TAG_GLOBAL_THEME_DANGER_BUTTON
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN,
    TAG_MAIN_CONVERTER_PROGRESS_SCAN,
    TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER,
    TAG_MAIN_CONVERTER_WINDOW_SCAN,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_shared.types.callback import VoidCallback

ROLL_STEP: Final[float] = 0.02
ROLL_WIDTH: Final[float] = 0.25
FULL: Final[float] = 1.0
NOTHING: Final[float] = 0.0


class GUIScanWindow(GUIWindow):
    """What the reader is waiting for while a folder is being read.

    Reading a folder of thousands takes seconds, so the wait is put on screen: the folder being
    read, how many recordings have turned up so far, an indicator that keeps moving while the walk
    does, and a **Stop**. The window stands beside the interface rather than over it, so the reader
    carries on with everything else while it reads.

    The indicator rolls rather than filling, since how much of a tree is left is not known until
    the walk reaches the end of it.
    """

    _claims_the_screen = False

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        language_manager: LanguageManager,
    ) -> None:
        self._title = language_manager["main.converter.title.scan_dialog"]
        self._opening = language_manager["main.converter.message.scan_opening"]
        self._progress = language_manager["main.converter.template.scan_progress"]
        self._stop_label = language_manager["main.converter.label.stop_scan_button"]
        self._root = Path()
        self._rolling = False
        self._position = NOTHING

        self.on_stop: Optional[VoidCallback] = None

        super().__init__(
            tag=TAG_MAIN_CONVERTER_WINDOW_SCAN,
            width=layout.scan.width,
            height=layout.scan.height,
        )

    def open(self, root: Path) -> None:
        """Says which folder is being read, and starts the indicator moving."""
        self._root = root
        self._position = NOTHING
        self.show()
        self._roll_on()

    def close(self) -> None:
        """Takes the window away, which is what a walk ending or giving up leaves behind."""
        self._rolling = False
        self.hide()

    def report(self, count: int) -> None:
        """Says how many recordings the walk has met so far."""
        dpg_set_value(
            TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER,
            self._progress.format(count=count, name=self._root.name),
        )

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The folder is named by :meth:`open` before the tree is built."""

    def create_window(self) -> None:
        with self.dialog_window(label=self._title, on_close=None):
            dpg.add_text(
                self._opening.format(name=self._root.name),
                tag=TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER,
                wrap=self.width,
            )
            dpg.add_progress_bar(
                tag=TAG_MAIN_CONVERTER_PROGRESS_SCAN,
                default_value=NOTHING,
                width=-1,
            )
            dpg.add_separator()
            GUIButton(
                tag=TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN,
                label=self._stop_label,
                callback=self._stop,
                width=-1,
                theme=ThemeRegistry.get(TAG_GLOBAL_THEME_DANGER_BUTTON),
            )

    def _stop(self) -> None:
        """Takes the window away and asks the walk to give up, which is what **Stop** means here.

        The window answers the gesture itself rather than the walk's next word, so pressing
        **Stop** is what closes it however the reading ends. A walk that reaches the end of its
        tree finds the window already gone and takes it away again, which leaves it where it is.
        """
        self.close()
        self.call(self.on_stop)

    def _roll_on(self) -> None:
        """Keeps the indicator moving for as long as the walk it stands for runs."""
        self._rolling = True
        FrameCallbackManager.set_frame_callback(self._roll)

    def _roll(self) -> None:
        if not self._rolling or not dpg.does_item_exist(TAG_MAIN_CONVERTER_PROGRESS_SCAN):
            return

        self._position = (self._position + ROLL_STEP) % (FULL + ROLL_WIDTH)
        dpg_set_value(TAG_MAIN_CONVERTER_PROGRESS_SCAN, min(self._position, FULL))
        dpg_configure_item(TAG_MAIN_CONVERTER_PROGRESS_SCAN, overlay="")
        FrameCallbackManager.set_frame_callback(self._roll)
