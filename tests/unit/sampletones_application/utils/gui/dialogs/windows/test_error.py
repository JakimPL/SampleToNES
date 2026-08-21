from typing import Final

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.config import LayoutConfig
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_BUTTON_OK,
    SUF_BUTTON_SHOW_TRACEBACK,
    SUF_GROUP,
    TAG_GLOBAL_DIALOG_ERROR,
)
from sampletones_application.utils.gui.dialogs import get_dialog_tag
from sampletones_application.utils.gui.dialogs.windows.error import (
    GUIErrorDialogWindow,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from tests.suite.shortcuts import shipped_source

LANGUAGE_MANAGER: Final[LanguageManager] = LanguageManager(LANG_EN)
WINDOW_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_ERROR)


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIErrorDialogWindow:
    return GUIErrorDialogWindow(
        tag=WINDOW_TAG,
        width=layout_config.general.dialogs.error.width,
        height=layout_config.general.dialogs.error.height,
        wrap=layout_config.general.dialogs.error.width - 10,
        language_manager=LANGUAGE_MANAGER,
        error_color=layout_config.general.colors.text.error,
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(window: GUIErrorDialogWindow, message: str = "context") -> None:
    """Builds the widget tree for the given failure, the way ``show`` does without a live frame."""
    window.prepare(RuntimeError("boom"), message)
    window.create_window()


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


class TestErrorWindow:
    def test_reports_the_exception_name_and_text(self, window: GUIErrorDialogWindow) -> None:
        render(window)

        texts = [dpg.get_value(item) for item in dpg.get_item_children(compose_tag(WINDOW_TAG, SUF_GROUP), 1)]
        assert any(text.startswith("RuntimeError") for text in texts)
        assert "boom" in texts

    def test_the_traceback_toggle_flips_its_label(self, window: GUIErrorDialogWindow) -> None:
        render(window)
        show_inner_tag = compose_tag(WINDOW_TAG, SUF_BUTTON_SHOW_TRACEBACK, SUF_BUTTON)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_SHOW_TRACEBACK))

        assert dpg.get_item_label(show_inner_tag) == LANGUAGE_MANAGER["global.traceback.label.hide"]

    def test_ok_dismisses_the_prompt(self, window: GUIErrorDialogWindow) -> None:
        render(window)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_OK))

        assert not dpg.does_item_exist(WINDOW_TAG)
