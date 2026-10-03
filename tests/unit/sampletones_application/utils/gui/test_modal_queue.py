from typing import Final, List

import pytest

from sampletones_application.utils.gui.modal_queue import ModalQueue
from sampletones_shared.types.callback import VoidCallback
from tests.suite.frames import Frames, held_frames

__all__ = ["held_frames"]

FIRST: Final[str] = "first"
SECOND: Final[str] = "second"
THIRD: Final[str] = "third"
DIALOG: Final[str] = "dialog"
PROMPT: Final[str] = "prompt"


class Screen:
    """The windows the line built, in the order it built them, and what each one stands for."""

    def __init__(self) -> None:
        self.built: List[str] = []
        self.revealed: List[str] = []

    def builder(self, tag: str) -> VoidCallback:
        return lambda: self.built.append(tag)

    def open(self, tag: str) -> None:
        ModalQueue.open(tag, self.builder(tag))

    def revealer(self, tag: str) -> VoidCallback:
        return lambda: self.revealed.append(tag)


@pytest.fixture
def screen() -> Screen:
    return Screen()


class TestTheFreeScreen:
    """A modal asked for while nothing holds the screen opens at once."""

    def test_the_first_modal_opens_at_once(self, screen: Screen) -> None:
        screen.open(FIRST)

        assert screen.built == [FIRST]

    def test_a_modal_left_frees_the_screen_a_frame_later(self, screen: Screen, held_frames: Frames) -> None:
        """The frame the modal left in still draws it, so a modal built there would open hidden."""
        screen.open(FIRST)
        ModalQueue.leave(FIRST)

        screen.open(SECOND)
        assert screen.built == [FIRST]

        held_frames.render()

        assert screen.built == [FIRST, SECOND]


class TestTheLine:
    """A modal asked for while another conversation holds the screen waits its turn."""

    def test_a_modal_asked_for_while_another_stands_waits(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(FIRST)

        screen.open(SECOND)
        held_frames.render()

        assert screen.built == [FIRST]

    def test_the_waiting_modal_opens_a_frame_after_the_standing_one_leaves(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        screen.open(FIRST)
        screen.open(SECOND)

        ModalQueue.leave(FIRST)
        assert screen.built == [FIRST]
        held_frames.render()

        assert screen.built == [FIRST, SECOND]

    def test_modals_waiting_open_in_the_order_they_were_asked_for(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        screen.open(FIRST)
        screen.open(SECOND)
        screen.open(THIRD)

        ModalQueue.leave(FIRST)
        held_frames.render()
        ModalQueue.leave(SECOND)
        held_frames.render()

        assert screen.built == [FIRST, SECOND, THIRD]

    def test_asking_again_for_a_waiting_modal_keeps_one_place_with_the_newer_request(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        newer: List[str] = []
        screen.open(FIRST)
        screen.open(SECOND)
        screen.open(THIRD)

        ModalQueue.open(SECOND, lambda: newer.append(SECOND))
        ModalQueue.leave(FIRST)
        held_frames.render()

        assert screen.built == [FIRST, THIRD]
        assert not newer

    def test_a_modal_taken_away_while_it_waits_never_opens(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(FIRST)
        screen.open(SECOND)

        ModalQueue.leave(SECOND)
        ModalQueue.leave(FIRST)
        held_frames.render()

        assert screen.built == [FIRST]


class TestAConversation:
    """A modal and what it hands the screen to keep the screen until the last of them leaves."""

    def test_what_an_answer_raises_opens_ahead_of_the_line(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(FIRST)
        screen.open(SECOND)

        ModalQueue.leave(FIRST)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()

        assert screen.built == [FIRST, PROMPT]

    def test_the_line_moves_once_the_answer_raised_nothing(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(FIRST)
        screen.open(SECOND)

        ModalQueue.leave(FIRST)
        ModalQueue.hand_off(lambda: None)
        held_frames.render()

        assert screen.built == [FIRST, SECOND]

    def test_a_dialog_standing_aside_keeps_the_screen_for_its_prompt(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        screen.open(DIALOG)
        screen.open(SECOND)

        ModalQueue.step_aside(DIALOG)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()

        assert screen.built == [DIALOG, PROMPT]

    def test_the_dialog_comes_back_ahead_of_the_line(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(DIALOG)
        screen.open(SECOND)
        ModalQueue.step_aside(DIALOG)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()

        ModalQueue.leave(PROMPT)
        ModalQueue.hand_off(lambda: ModalQueue.come_back(DIALOG, screen.revealer(DIALOG)))
        held_frames.render()

        assert screen.revealed == [DIALOG]
        assert screen.built == [DIALOG, PROMPT]

    def test_the_line_moves_once_the_dialog_itself_leaves(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(DIALOG)
        screen.open(SECOND)
        ModalQueue.step_aside(DIALOG)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()

        ModalQueue.leave(PROMPT)
        ModalQueue.hand_off(lambda: ModalQueue.leave(DIALOG))
        held_frames.render(2)

        assert screen.built == [DIALOG, PROMPT, SECOND]

    def test_a_second_modal_one_answer_raises_waits_for_the_first(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        """DearPyGui shows one of them, so the answer's second modal opens once its first one leaves."""
        screen.open(FIRST)
        screen.open(THIRD)
        ModalQueue.leave(FIRST)

        def answer() -> None:
            screen.open(PROMPT)
            screen.open(SECOND)

        ModalQueue.hand_off(answer)
        held_frames.render()
        ModalQueue.leave(PROMPT)
        held_frames.render()

        assert screen.built == [FIRST, PROMPT, SECOND]

    def test_a_modal_raised_where_the_answer_closed_one_opens_a_frame_later(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        """The frame the answer closed a modal in still draws it, and the answer's modal keeps its turn."""
        screen.open(DIALOG)
        screen.open(THIRD)

        def answer() -> None:
            ModalQueue.leave(DIALOG)
            screen.open(SECOND)

        ModalQueue.hand_off(answer)
        held_frames.render()
        assert screen.built == [DIALOG]

        held_frames.render()

        assert screen.built == [DIALOG, SECOND]

    def test_closing_a_dialog_standing_aside_frees_the_screen_at_once(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        """A dialog standing aside is drawn nowhere, so the screen it leaves is free in the same frame."""
        screen.open(DIALOG)
        ModalQueue.step_aside(DIALOG)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()
        ModalQueue.leave(PROMPT)
        held_frames.render()

        def answer() -> None:
            ModalQueue.leave(DIALOG)
            screen.open(SECOND)

        ModalQueue.hand_off(answer)
        held_frames.render()

        assert screen.built == [DIALOG, PROMPT, SECOND]


class TestTheSnapshot:
    """A reader outside the line sees which window stands, which wait, and whether the line moves."""

    def test_a_free_screen_reads_settled(self) -> None:
        snapshot = ModalQueue.snapshot()

        assert snapshot.shown is None
        assert snapshot.is_settled

    def test_the_standing_window_and_the_line_read_in_order(self, screen: Screen) -> None:
        screen.open(FIRST)
        screen.open(SECOND)
        screen.open(THIRD)

        snapshot = ModalQueue.snapshot()

        assert snapshot.shown == FIRST
        assert snapshot.waiting == (SECOND, THIRD)
        assert not snapshot.is_settled

    @pytest.mark.usefixtures("held_frames")
    def test_a_window_that_left_reads_as_a_turn_due(self, screen: Screen) -> None:
        screen.open(FIRST)

        ModalQueue.leave(FIRST)

        snapshot = ModalQueue.snapshot()
        assert snapshot.shown is None
        assert snapshot.turning
        assert not snapshot.is_settled

    def test_the_line_settles_a_frame_after_the_last_window_left(
        self,
        screen: Screen,
        held_frames: Frames,
    ) -> None:
        screen.open(FIRST)
        ModalQueue.leave(FIRST)

        held_frames.render()

        assert ModalQueue.snapshot().is_settled

    def test_a_dialog_standing_aside_reads_aside(self, screen: Screen, held_frames: Frames) -> None:
        screen.open(DIALOG)
        ModalQueue.step_aside(DIALOG)
        ModalQueue.hand_off(lambda: screen.open(PROMPT))
        held_frames.render()

        snapshot = ModalQueue.snapshot()

        assert snapshot.shown == PROMPT
        assert snapshot.aside == (DIALOG,)
        assert not snapshot.is_settled
