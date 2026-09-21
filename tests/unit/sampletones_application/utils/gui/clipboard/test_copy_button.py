from typing import Final, Iterator, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.loader import load_layout_config
from sampletones_application.paths import (
    BEHAVIOR_DIRECTORY,
    LAYOUT_DIRECTORY,
    PALETTES_DIRECTORY,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.themes.items import ThemeItems
from sampletones_application.ui.themes.theme import Theme
from sampletones_application.utils.gui.clipboard import copy_button as copy_button_module
from sampletones_application.utils.gui.clipboard.copy_button import (
    COPIED_LABEL_SECONDS,
    copy_to_clipboard,
)
from sampletones_application.utils.palette.catalog import PaletteCatalog
from sampletones_application.utils.palette.source import PaletteSource
from tests.suite.application import ManualClock, draw_frame
from tests.suite.base import BaseTestSuite

WINDOW: Final[str] = "probe.window"
BUTTON: Final[str] = "probe.window.button.copy"
THEME: Final[str] = "probe.theme"
LABEL: Final[str] = "Copy"
COPIED: Final[str] = "Copied"
TEXT: Final[str] = "the text a reader copies"
QUEUE_LOGGER: Final[str] = "sampletones_application.utils.callbacks.queue.logger"


@pytest.fixture
def written(monkeypatch: pytest.MonkeyPatch) -> List[str]:
    """What reaches the desktop's clipboard, held here so a case leaves the reader's own alone."""
    texts: List[str] = []
    monkeypatch.setattr(copy_button_module.dpg, "set_clipboard_text", texts.append)
    return texts


@pytest.fixture
def copy_button() -> Iterator[GUIButton]:
    """A Copy button standing in a window, built the way the traceback and the instruments build theirs."""
    layout_config = load_layout_config(
        LAYOUT_DIRECTORY,
        BEHAVIOR_DIRECTORY,
        PaletteSource(PaletteCatalog.load(PALETTES_DIRECTORY).default),
    )
    dpg.create_context()
    FontRegistry.setup(layout_config.fonts)
    FontRegistry.register_fonts(layout_config.fonts.scale)
    try:
        with dpg.window(tag=WINDOW):
            button = GUIButton(
                tag=BUTTON,
                label=LABEL,
                parent=WINDOW,
                theme=Theme(tag=THEME, items=ThemeItems()),
            )

        yield button
    finally:
        GUIButton.delete(BUTTON)
        dpg.destroy_context()


@pytest.mark.usefixtures("live_queue", "written")
class TestCopyingWithTheButton(BaseTestSuite):
    """A press puts the text on the clipboard and says so on the button for a moment."""

    def test_the_text_reaches_the_clipboard(self, copy_button: GUIButton, written: List[str]) -> None:
        copy_to_clipboard(TEXT, LABEL, BUTTON, copied_label=COPIED)

        assert written == [TEXT]

    def test_the_button_says_copied_while_the_moment_stands(
        self,
        copy_button: GUIButton,
        delay_clock: ManualClock,
    ) -> None:
        copy_to_clipboard(TEXT, LABEL, BUTTON, copied_label=COPIED)
        draw_frame()

        assert copy_button.get_item_label() == COPIED

    def test_the_button_reads_its_own_label_once_the_moment_passes(
        self,
        copy_button: GUIButton,
        delay_clock: ManualClock,
    ) -> None:
        copy_to_clipboard(TEXT, LABEL, BUTTON, copied_label=COPIED)
        delay_clock.advance(COPIED_LABEL_SECONDS)
        draw_frame()

        assert copy_button.get_item_label() == LABEL

    def test_a_button_closed_within_the_moment_is_passed_over(
        self,
        copy_button: GUIButton,
        delay_clock: ManualClock,
    ) -> None:
        """The error dialog carrying a Copy button can be closed before its label comes back."""
        copy_to_clipboard(TEXT, LABEL, BUTTON, copied_label=COPIED)
        dpg.delete_item(BUTTON)
        delay_clock.advance(COPIED_LABEL_SECONDS)
        with patch(QUEUE_LOGGER) as queue_logger:
            draw_frame()

        queue_logger.error_with_traceback.assert_not_called()
