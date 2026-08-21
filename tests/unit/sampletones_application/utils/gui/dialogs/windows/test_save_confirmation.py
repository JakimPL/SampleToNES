from typing import Final, List

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_BUTTON_SAVE,
    TAG_GLOBAL_DIALOG_FILE_NOT_FOUND,
)
from sampletones_application.utils.gui.dialogs import get_dialog_tag
from sampletones_application.utils.gui.dialogs.windows.save_confirmation import (
    GUISaveConfirmationWindow,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from tests.suite.shortcuts import shipped_source

WINDOW_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)
CONFIRMED: Final[str] = "confirmed"


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUISaveConfirmationWindow:
    return GUISaveConfirmationWindow(
        tag=WINDOW_TAG,
        width=layout_config.general.dialogs.default.width,
        height=layout_config.general.dialogs.confirmation.height,
        wrap=layout_config.general.dialogs.default.width - 10,
        save_label="Save",
        cancel_label="Cancel",
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(
    window: GUISaveConfirmationWindow,
    *,
    save_succeeds: bool,
    answers: List[str],
) -> None:
    """Builds the prompt for the given save, the way ``show`` does without a live frame."""
    window.prepare(
        "Save first?",
        "Title",
        lambda: save_succeeds,
        lambda: answers.append(CONFIRMED),
        ok_label="Proceed",
    )
    window.create_window()


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


class TestSaveConfirmationWindow:
    def test_a_cancelled_save_keeps_the_prompt_open(self, window: GUISaveConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, save_succeeds=False, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_SAVE))

        assert answers == []
        assert dpg.does_item_exist(WINDOW_TAG)

    def test_a_completed_save_proceeds_and_closes(self, window: GUISaveConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, save_succeeds=True, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_SAVE))

        assert answers == [CONFIRMED]
        assert not dpg.does_item_exist(WINDOW_TAG)

    def test_the_middle_button_proceeds_without_saving(self, window: GUISaveConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, save_succeeds=False, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_OK))

        assert answers == [CONFIRMED]
        assert not dpg.does_item_exist(WINDOW_TAG)

    def test_cancel_dismisses_the_prompt(self, window: GUISaveConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, save_succeeds=False, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_CANCEL))

        assert answers == []
        assert not dpg.does_item_exist(WINDOW_TAG)
