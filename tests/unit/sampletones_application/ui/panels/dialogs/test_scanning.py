from pathlib import Path
from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, TAG_GLOBAL_THEME_DANGER_BUTTON
from sampletones_application.tags.main import (
    TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN,
    TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER,
    TAG_MAIN_CONVERTER_WINDOW_SCAN,
)
from sampletones_application.ui.panels.dialogs.scanning import GUIScanWindow
from tests.suite.base import BaseTestSuite

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
OPENING: Final[str] = LANGUAGE_MANAGER["main.converter.message.scan_opening"]
PROGRESS: Final[str] = LANGUAGE_MANAGER["main.converter.template.scan_progress"]
ROOT: Final[Path] = Path("/music/takes")
FOUND: Final[int] = 128


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIScanWindow:
    return GUIScanWindow(
        layout=layout_config.tabs.main.converter,
        language_manager=LANGUAGE_MANAGER,
    )


def open_on(window: GUIScanWindow, root: Path) -> None:
    """Names the folder and builds the tree, the way ``open`` does without a live frame."""
    window.open(root)


def press_stop() -> None:
    dpg.get_item_callback(compose_tag(TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN, SUF_BUTTON))()


class TestWhatTheWindowSays(BaseTestSuite):
    """The reader is told which folder is being read and how far the walk has got."""

    def test_it_opens_on_the_folder_it_was_given(self, window: GUIScanWindow) -> None:
        open_on(window, ROOT)

        assert dpg.get_value(TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER) == OPENING.format(name=ROOT.name)

    def test_it_counts_what_the_walk_has_met(self, window: GUIScanWindow) -> None:
        open_on(window, ROOT)

        window.report(FOUND)

        assert dpg.get_value(TAG_MAIN_CONVERTER_TEXT_SCAN_FOLDER) == PROGRESS.format(count=FOUND, name=ROOT.name)


class TestHowStopReads(BaseTestSuite):
    """Stop gives up on a reading the reader asked for, so it carries the tone the interface
    gives an action that undoes what is under way."""

    def test_stop_carries_the_tone_of_the_action_it_is(self, window: GUIScanWindow) -> None:
        open_on(window, ROOT)

        theme = dpg.get_item_theme(compose_tag(TAG_MAIN_CONVERTER_BUTTON_STOP_SCAN, SUF_BUTTON))

        assert dpg.get_item_alias(theme) == TAG_GLOBAL_THEME_DANGER_BUTTON


class TestGivingUp(BaseTestSuite):
    """Stop is answered by the window itself, so it closes however the reading ends.

    The window carries no close of its own, and a walk that dies partway reports nothing, so a
    Stop that waited for the walk's next word would leave the reader a window with no way out.
    """

    def test_stop_takes_the_window_away(self, window: GUIScanWindow) -> None:
        open_on(window, ROOT)

        press_stop()

        assert dpg.does_item_exist(TAG_MAIN_CONVERTER_WINDOW_SCAN) is False

    def test_stop_asks_the_walk_to_give_up(self, window: GUIScanWindow) -> None:
        asked: List[bool] = []
        window.on_stop = lambda: asked.append(True)
        open_on(window, ROOT)

        press_stop()

        assert asked == [True]

    def test_a_walk_ending_after_stop_leaves_the_window_gone(self, window: GUIScanWindow) -> None:
        open_on(window, ROOT)
        press_stop()

        window.close()

        assert dpg.does_item_exist(TAG_MAIN_CONVERTER_WINDOW_SCAN) is False
