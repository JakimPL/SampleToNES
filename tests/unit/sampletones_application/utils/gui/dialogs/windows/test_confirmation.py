from pathlib import Path
from typing import Final, List
from unittest.mock import MagicMock

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.layout.config import LayoutConfig
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import (
    SUF_BUTTON,
    SUF_BUTTON_CANCEL,
    SUF_BUTTON_OK,
    SUF_CHECKBOX,
    TAG_GLOBAL_DIALOG_PATH_MESSAGE,
)
from sampletones_application.utils.gui.dialogs import get_dialog_tag
from sampletones_application.utils.gui.dialogs.windows.confirmation import (
    GUIConfirmationWindow,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from tests.suite.shortcuts import shipped_source

WINDOW_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_PATH_MESSAGE)
CONFIRMED: Final[str] = "confirmed"
CANCELLED: Final[str] = "cancelled"
OPTED_OUT: Final[str] = "opted_out"


@pytest.fixture(name="window")
def window_fixture(dpg_context: None, layout_config: LayoutConfig) -> GUIConfirmationWindow:
    return GUIConfirmationWindow(
        tag=WINDOW_TAG,
        width=layout_config.general.dialogs.default.width,
        height=layout_config.general.dialogs.confirmation.height,
        wrap=layout_config.general.dialogs.default.width - 10,
        path_color=layout_config.general.colors.paths.default,
        path_hover_color=layout_config.general.colors.paths.hover,
        path_message="path",
        status_bar=MagicMock(),
        key_router=KeyRouter(),
        shortcut_source=shipped_source(),
    )


def render(
    window: GUIConfirmationWindow,
    *,
    path: Path | None = None,
    opt_out_label: str | None = None,
    answers: List[str] | None = None,
) -> None:
    """Builds the prompt for the given question, the way ``show`` does without a live frame."""
    window.prepare(
        "Save it?",
        "Title",
        lambda: answers.append(CONFIRMED) if answers is not None else None,
        ok_label="Yes",
        cancel_label="No",
        path=path,
        opt_out_label=opt_out_label,
        on_opt_out=lambda: answers.append(OPTED_OUT) if answers is not None else None,
        on_cancel=lambda: answers.append(CANCELLED) if answers is not None else None,
    )
    window.create_window()


def press(tag: str) -> None:
    dpg.get_item_callback(compose_tag(tag, SUF_BUTTON))()


class TestConfirmationWindow:
    def test_ok_runs_the_confirmation_and_closes(self, window: GUIConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_OK))

        assert answers == [CONFIRMED]
        assert not dpg.does_item_exist(WINDOW_TAG)

    def test_cancel_runs_the_negative_answer_and_closes(self, window: GUIConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_CANCEL))

        assert answers == [CANCELLED]
        assert not dpg.does_item_exist(WINDOW_TAG)

    def test_a_ticked_opt_out_rides_the_confirmation(self, window: GUIConfirmationWindow) -> None:
        answers: List[str] = []
        render(window, opt_out_label="Do not ask again", answers=answers)
        dpg.set_value(compose_tag(WINDOW_TAG, SUF_CHECKBOX), True)

        press(compose_tag(WINDOW_TAG, SUF_BUTTON_OK))

        assert answers == [OPTED_OUT, CONFIRMED]

    def test_the_path_is_shown_when_given(self, window: GUIConfirmationWindow, tmp_path: Path) -> None:
        path = tmp_path / "song.stn"

        render(window, path=path)

        assert dpg.does_item_exist(compose_tag(WINDOW_TAG, "path"))
