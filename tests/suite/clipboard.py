from typing import List, Optional

from sampletones_application.utils.gui.clipboard.protocol import ClipboardTextCallback


class FakeTextClipboard:
    """The desktop's clipboard, held in memory so a test reads what a copy put there.

    A read is answered at once, the way DearPyGui's own clipboard answers, until a case holds the
    answers back to stand for an application that hands its text over later, or none at all.
    """

    def __init__(self) -> None:
        self.text: str = ""
        self.unanswered: List[ClipboardTextCallback] = []
        self._answers_held: bool = False

    def read(self, on_text: ClipboardTextCallback) -> None:
        if self._answers_held:
            self.unanswered.append(on_text)
            return

        on_text(self.text)

    def write(self, text: str) -> None:
        self.text = text

    def hold_answers(self) -> None:
        self._answers_held = True

    def answer(self) -> None:
        """Hands the text standing now to every read still waiting, in the order they asked."""
        self._hand_over(self.text)

    def silence(self) -> None:
        """Leaves every read still waiting with no answer, the way an owner that never replies does."""
        self._hand_over(None)

    def _hand_over(self, text: Optional[str]) -> None:
        waiting, self.unanswered = self.unanswered, []
        for on_text in waiting:
            on_text(text)
