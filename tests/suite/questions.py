from dataclasses import dataclass
from typing import Final, List, Optional

import pytest

from sampletones_application.utils.callbacks.gates import Gate, asking
from sampletones_application.utils.gui.modal_queue import ModalQueue
from sampletones_shared.types.callback import VoidCallback
from tests.suite.frames import Frames

STANDING_WINDOW: Final[str] = "standing window"


class StandingWindow:
    """Another conversation holding the screen, such as a dialog the reader has open."""

    def __init__(self, frames: Frames) -> None:
        self._frames = frames

    def stand(self) -> None:
        ModalQueue.open(STANDING_WINDOW, lambda: None)

    def leave(self) -> None:
        """Takes the window off the screen and renders the frame the line moves on in."""
        ModalQueue.leave(STANDING_WINDOW)
        self._frames.render()


@pytest.fixture
def standing_window(held_frames: Frames) -> StandingWindow:
    """A window standing on the screen, which a case takes away when it wants the screen free."""
    window = StandingWindow(held_frames)
    window.stand()
    return window


@dataclass(frozen=True)
class StandingQuestion:
    """A question on the screen, with the two ways out of it."""

    tag: str
    proceed: VoidCallback
    decline: VoidCallback


class OnScreenDocument:
    """Something unfinished whose owner asks about it on the screen, the way the application's guards do.

    A guard asks once the screen is free for its question, and reads whether the thing is unfinished
    then. An answer leaves the screen first and runs a frame later, as a dialog's answer does, so a case
    renders a frame between the answer and what it lets through.
    """

    def __init__(self, name: str, asked: List[str]) -> None:
        self.name = name
        self.unfinished = False
        self._asked = asked
        self._standing: Optional[StandingQuestion] = None

    def guard(self, question: str) -> Gate:
        """The gate that asks ``question`` while the thing is unfinished, and lets the request through otherwise.

        The question is recorded in the shared ``asked`` list as ``"<name> <question>"`` once it reaches
        the screen.
        """

        tag = f"{self.name} {question}"

        def ask(proceed: VoidCallback, decline: VoidCallback) -> None:
            def build() -> None:
                self._asked.append(tag)
                self._standing = StandingQuestion(tag=tag, proceed=proceed, decline=decline)

            ModalQueue.open(tag, build)

        return asking(lambda: self.unfinished, ask, ModalQueue.when_free)

    def finish(self) -> None:
        """Settles the thing, the way closing a document lets its changes go or a run comes to its end."""
        self.unfinished = False

    def go_on(self) -> None:
        """The reader answering the question standing with Save, Discard or Exit."""
        question = self._take_question()
        ModalQueue.hand_off(question.proceed)

    def cancel(self) -> None:
        """The reader answering the question standing with Cancel."""
        question = self._take_question()
        ModalQueue.hand_off(question.decline)

    def _take_question(self) -> StandingQuestion:
        """Takes the question standing off the screen, the way an answered dialog leaves before its answer runs."""
        assert self._standing is not None, f"No question about the {self.name} stands"
        question, self._standing = self._standing, None
        ModalQueue.leave(question.tag)
        return question
