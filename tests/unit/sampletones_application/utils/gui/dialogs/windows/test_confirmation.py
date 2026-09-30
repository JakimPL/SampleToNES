from pathlib import Path
from typing import Final, List, Optional
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
    TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION,
    TAG_GLOBAL_DIALOG_PATH_MESSAGE,
)
from sampletones_application.utils.gui.dialogs import get_dialog_tag
from sampletones_application.utils.gui.dialogs.windows.confirmation import (
    GUIConfirmationWindow,
)
from sampletones_application.utils.gui.keyboard import KeyEvent, KeyRouter
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_shared.types.callback import VoidCallback
from tests.suite.frames import Frames
from tests.suite.shortcuts import shipped_scheme, shipped_source

WINDOW_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_PATH_MESSAGE)
FOLLOWING_TAG: Final[str] = get_dialog_tag(TAG_GLOBAL_DIALOG_EXIT_CONFIRMATION)
CONFIRMED: Final[str] = "confirmed"
CANCELED: Final[str] = "canceled"
OPTED_OUT: Final[str] = "opted_out"
FOLLOWING_CANCELED: Final[str] = "following_canceled"


@pytest.fixture(name="router")
def router_fixture() -> KeyRouter:
    return KeyRouter()


def build_window(tag: str, layout_config: LayoutConfig, router: KeyRouter) -> GUIConfirmationWindow:
    return GUIConfirmationWindow(
        tag=tag,
        geometry=layout_config.general.dialogs.confirmation,
        wrap=layout_config.general.dialogs.default.width - 10,
        path_color=layout_config.general.colors.paths.default,
        path_hover_color=layout_config.general.colors.paths.hover,
        path_message="path",
        status_bar=MagicMock(),
        key_router=router,
        shortcut_source=shipped_source(),
    )


@pytest.fixture(name="window")
def window_fixture(
    dpg_context: None,
    layout_config: LayoutConfig,
    router: KeyRouter,
) -> GUIConfirmationWindow:
    return build_window(WINDOW_TAG, layout_config, router)


def render(
    window: GUIConfirmationWindow,
    *,
    answers: List[str],
    path: Optional[Path] = None,
    opt_out_label: Optional[str] = None,
    on_confirm: Optional[VoidCallback] = None,
) -> None:
    """Builds the prompt for the given question, the way ``show`` does without a live frame."""
    window.prepare(
        "Save it?",
        "Title",
        on_confirm if on_confirm is not None else lambda: answers.append(CONFIRMED),
        ok_label="Yes",
        cancel_label="No",
        path=path,
        opt_out_label=opt_out_label,
        on_opt_out=lambda: answers.append(OPTED_OUT),
        on_cancel=lambda: answers.append(CANCELED),
    )
    window.create_window()


def button_callback(window_tag: str, suffix: str) -> VoidCallback:
    """What a click on one of the prompt's buttons runs, read while the button stands."""
    callback = dpg.get_item_callback(compose_tag(compose_tag(window_tag, suffix), SUF_BUTTON))
    assert callback is not None
    return callback


def press(window_tag: str, suffix: str) -> None:
    button_callback(window_tag, suffix)()


def escape(router: KeyRouter) -> None:
    """The press the shipped scheme cancels a dialog with, routed the way the keyboard sends it."""
    combination = shipped_scheme().shortcut(ShortcutId.DIALOG_CANCEL).combination
    assert combination is not None
    router.route(KeyEvent(key=combination.key, modifiers=combination.modifiers))


class TestAnAnswerRunsOnceThePromptHasLeft:
    """DearPyGui carries one modal at a time, so whatever an answer raises waits for the prompt to go."""

    def test_ok_leaves_the_screen_before_it_answers(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(WINDOW_TAG, SUF_BUTTON_OK)

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == []

    def test_ok_confirms_a_frame_later(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(WINDOW_TAG, SUF_BUTTON_OK)
        held_frames.render()

        assert answers == [CONFIRMED]

    def test_cancel_leaves_the_screen_before_it_answers(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(WINDOW_TAG, SUF_BUTTON_CANCEL)

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == []

    def test_cancel_answers_the_negative_choice_a_frame_later(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        press(WINDOW_TAG, SUF_BUTTON_CANCEL)
        held_frames.render()

        assert answers == [CANCELED]

    def test_escape_answers_as_cancel(
        self,
        window: GUIConfirmationWindow,
        router: KeyRouter,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        escape(router)
        held_frames.render()

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == [CANCELED]

    def test_the_title_bar_close_answers_as_cancel(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers)

        dpg.get_item_configuration(WINDOW_TAG)["on_close"]()
        held_frames.render()

        assert not dpg.does_item_exist(WINDOW_TAG)
        assert answers == [CANCELED]

    def test_a_ticked_opt_out_rides_the_confirmation(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        """The box is read as the reader leaves, since the answer runs once it has been deleted."""
        answers: List[str] = []
        render(window, answers=answers, opt_out_label="Do not ask again")
        dpg.set_value(compose_tag(WINDOW_TAG, SUF_CHECKBOX), True)

        press(WINDOW_TAG, SUF_BUTTON_OK)
        held_frames.render()

        assert not dpg.does_item_exist(compose_tag(WINDOW_TAG, SUF_CHECKBOX))
        assert answers == [OPTED_OUT, CONFIRMED]

    def test_a_clear_opt_out_confirms_alone(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        answers: List[str] = []
        render(window, answers=answers, opt_out_label="Do not ask again")

        press(WINDOW_TAG, SUF_BUTTON_OK)
        held_frames.render()

        assert answers == [CONFIRMED]

    def test_the_keyboard_is_free_when_the_answer_runs(
        self,
        window: GUIConfirmationWindow,
        router: KeyRouter,
        held_frames: Frames,
    ) -> None:
        """A prompt the answer raises claims the keyboard on its own, over whatever stood beneath."""
        claims: List[bool] = []
        render(window, answers=[], on_confirm=lambda: claims.append(router.is_modal_open))

        press(WINDOW_TAG, SUF_BUTTON_OK)
        held_frames.render()

        assert claims == [False]

    def test_a_second_press_answers_nothing(
        self,
        window: GUIConfirmationWindow,
        held_frames: Frames,
    ) -> None:
        """A click DearPyGui delivers after the first one reaches a prompt that has already left."""
        answers: List[str] = []
        render(window, answers=answers)
        confirm = button_callback(WINDOW_TAG, SUF_BUTTON_OK)
        cancel = button_callback(WINDOW_TAG, SUF_BUTTON_CANCEL)

        confirm()
        confirm()
        cancel()
        held_frames.render()

        assert answers == [CONFIRMED]
        assert held_frames.pending == 0

    def test_the_path_is_shown_when_given(
        self,
        window: GUIConfirmationWindow,
        tmp_path: Path,
    ) -> None:
        render(window, answers=[], path=tmp_path / "song.stn")

        assert dpg.does_item_exist(compose_tag(WINDOW_TAG, "path"))


class TestAPromptRaisedFromAnAnswer:
    """An answer asking a question of its own — "Load it now?" leading to "Save your changes?" —
    raises a second prompt, which stands alone and answers the keyboard."""

    @pytest.fixture(name="answers")
    def answers_fixture(
        self,
        window: GUIConfirmationWindow,
        layout_config: LayoutConfig,
        router: KeyRouter,
        held_frames: Frames,
    ) -> List[str]:
        answers: List[str] = []
        following = build_window(FOLLOWING_TAG, layout_config, router)

        def ask_again() -> None:
            answers.append(f"first_standing={dpg.does_item_exist(WINDOW_TAG)}")
            following.prepare(
                "Save your changes?",
                "Title",
                lambda: answers.append(CONFIRMED),
                ok_label="Save",
                cancel_label="Cancel",
                path=None,
                opt_out_label=None,
                on_opt_out=None,
                on_cancel=lambda: answers.append(FOLLOWING_CANCELED),
            )
            following.create_window()

        render(window, answers=answers, on_confirm=ask_again)
        press(WINDOW_TAG, SUF_BUTTON_OK)
        held_frames.render()
        return answers

    def test_the_first_prompt_is_gone_when_the_second_is_built(self, answers: List[str]) -> None:
        assert answers == ["first_standing=False"]

    def test_the_second_prompt_stands(self, answers: List[str]) -> None:
        assert dpg.does_item_exist(FOLLOWING_TAG)

    def test_the_second_prompt_holds_the_keyboard(self, answers: List[str], router: KeyRouter) -> None:
        assert router.is_modal_open

    def test_escape_reaches_the_second_prompt(
        self,
        answers: List[str],
        router: KeyRouter,
        held_frames: Frames,
    ) -> None:
        escape(router)
        held_frames.render()

        assert answers[1:] == [FOLLOWING_CANCELED]
        assert not dpg.does_item_exist(FOLLOWING_TAG)
