from typing import Final, Iterator, List
from unittest.mock import patch

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
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_application.utils.gui.dialogs.windows.save_confirmation import (
    GUISaveConfirmationWindow,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_shared.types.callback import VoidCallback
from tests.suite.frames import Frames
from tests.suite.shortcuts import shipped_source

WINDOW_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_FILE_NOT_FOUND)
MESSAGE: Final[str] = "Save first?"
SAVED: Final[str] = "saved"
CONFIRMED: Final[str] = "confirmed"


@pytest.fixture(name="router")
def router_fixture() -> KeyRouter:
    return KeyRouter()


@pytest.fixture(name="window")
def window_fixture(
    dpg_context: None,
    layout_config: LayoutConfig,
    router: KeyRouter,
) -> GUISaveConfirmationWindow:
    return GUISaveConfirmationWindow(
        tag=WINDOW_TAG,
        geometry=layout_config.general.dialogs.confirmation,
        wrap=layout_config.general.dialogs.default.width - 10,
        save_label="Save",
        cancel_label="Cancel",
        key_router=router,
        shortcut_source=shipped_source(),
    )


def render(
    window: GUISaveConfirmationWindow,
    *,
    save_outcome: SaveOutcome,
    answers: List[str],
) -> None:
    """Builds the prompt for the given save, the way ``show`` does without a live frame."""

    def save() -> SaveOutcome:
        answers.append(SAVED)
        return save_outcome

    window.prepare(
        MESSAGE,
        "Title",
        save,
        lambda: answers.append(CONFIRMED),
        ok_label="Proceed",
    )
    window.create_window()


def button_callback(suffix: str) -> VoidCallback:
    callback = dpg.get_item_callback(compose_tag(compose_tag(WINDOW_TAG, suffix), SUF_BUTTON))
    assert callback is not None
    return callback


def press(suffix: str) -> None:
    button_callback(suffix)()


@pytest.fixture(name="placed")
def placed_fixture(layout_config: LayoutConfig) -> Iterator[None]:
    """Stands in for the viewport a prompt raised again is centered against, which a suite draws none of."""
    window = layout_config.general.window
    with (
        patch.object(dpg, "get_viewport_client_width", return_value=window.width),
        patch.object(dpg, "get_viewport_client_height", return_value=window.height),
    ):
        yield


class TestSavingFromThePrompt:
    """Save writes the document once the prompt has left, so whatever the save opens stands alone."""

    def test_save_leaves_the_screen_before_it_writes(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.WRITTEN, answers=answers)

        press(SUF_BUTTON_SAVE)

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == []

    def test_a_written_document_goes_on(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.WRITTEN, answers=answers)

        press(SUF_BUTTON_SAVE)
        held_frames.render()

        assert answers == [SAVED, CONFIRMED]
        assert not dpg.does_item_exist(WINDOW_TAG)

    def test_a_save_called_off_brings_the_prompt_back(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
        placed: None,
    ) -> None:
        """A reader who closes the file dialog without a name is asked the same question again."""
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.CALLED_OFF, answers=answers)

        press(SUF_BUTTON_SAVE)
        held_frames.render()

        assert answers == [SAVED]
        assert dpg.does_item_exist(WINDOW_TAG)
        assert dpg.get_item_label(WINDOW_TAG) == "Title"

    def test_the_prompt_back_answers_as_it_did(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
        placed: None,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.CALLED_OFF, answers=answers)
        press(SUF_BUTTON_SAVE)
        held_frames.render()

        press(SUF_BUTTON_OK)
        held_frames.render()

        assert answers == [SAVED, CONFIRMED]

    def test_the_prompt_back_holds_the_keyboard_once(
        self,
        window: GUISaveConfirmationWindow,
        router: KeyRouter,
        held_frames: Frames,
        placed: None,
    ) -> None:
        render(window, save_outcome=SaveOutcome.CALLED_OFF, answers=[])
        press(SUF_BUTTON_SAVE)
        held_frames.render()

        assert len(router._modal_stack) == 1

    def test_a_failed_save_leaves_the_error_alone_on_screen(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.FAILED, answers=answers)

        press(SUF_BUTTON_SAVE)
        held_frames.render()

        assert answers == [SAVED]
        assert not dpg.does_item_exist(WINDOW_TAG)
        assert held_frames.pending == 0


class TestTheOtherAnswers:
    def test_the_middle_button_goes_on_once_the_prompt_has_left(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.WRITTEN, answers=answers)

        press(SUF_BUTTON_OK)

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == []
        held_frames.render()
        assert answers == [CONFIRMED]

    def test_cancel_leaves_and_answers_nothing(
        self,
        window: GUISaveConfirmationWindow,
        router: KeyRouter,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.WRITTEN, answers=answers)

        press(SUF_BUTTON_CANCEL)
        held_frames.render()

        assert answers == []
        assert not dpg.does_item_exist(WINDOW_TAG)
        assert not router.is_modal_open

    def test_a_second_press_answers_nothing(
        self,
        window: GUISaveConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, save_outcome=SaveOutcome.WRITTEN, answers=answers)
        save = button_callback(SUF_BUTTON_SAVE)
        discard = button_callback(SUF_BUTTON_OK)

        save()
        discard()
        held_frames.render()

        assert answers == [SAVED, CONFIRMED]
