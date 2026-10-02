from typing import List, Optional, Tuple

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_BUTTON, SUF_BUTTON_CANCEL, SUF_BUTTON_OK, SUF_BUTTON_SAVE
from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import (
    BUTTON_TYPE,
    WindowReading,
    is_tag_within,
    read_shown_labels,
    read_shown_texts,
    read_windows,
)


class MissingPromptError(AssertionError):
    """Raised when a scenario answers a prompt that stands nowhere on the screen."""


class Prompt:
    """A question the application asks in a dialog of its own, found by the tag its kind composes under.

    Each prompt the application opens carries a fresh suffix on its kind's tag, so the prompt is the
    shown window standing under that tag, and its buttons are composed from the window it stands in.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tag: str,
    ) -> None:
        self._bridge = bridge
        self._hand = hand
        self._tag = tag

    def window(self) -> Optional[WindowReading]:
        """The prompt's window while one is shown, and ``None`` otherwise."""
        shown = self.shown_windows()
        return shown[0] if shown else None

    def shown_windows(self) -> List[WindowReading]:
        """Every window of the prompt's kind standing on the screen, which is one for a question asked once."""
        return [
            window
            for window in self._bridge.ask(read_windows)
            if window.shown and is_tag_within(window.alias, self._tag)
        ]

    def is_shown(self) -> bool:
        return self.window() is not None

    def title(self) -> str:
        """The title the prompt's window carries."""
        return self._standing().label

    def words(self) -> str:
        """Everything the prompt says, its lines joined by spaces."""
        window = self._standing()
        texts: Tuple[str, ...] = self._bridge.ask(lambda: read_shown_texts(window.alias))
        return " ".join(texts)

    def answers(self) -> Tuple[str, ...]:
        """The buttons the prompt offers, read left to right."""
        window = self._standing()
        return self._bridge.ask(lambda: read_shown_labels(window.alias, BUTTON_TYPE))

    def confirm(self) -> None:
        """Presses the button that says yes: Discard, Load, Exit and the like."""
        self._press(SUF_BUTTON_OK)

    def save(self) -> None:
        """Presses Save on a prompt that offers to save first."""
        self._press(SUF_BUTTON_SAVE)

    def cancel(self) -> None:
        """Presses the button that takes the question back."""
        self._press(SUF_BUTTON_CANCEL)

    def _press(self, suffix: str) -> None:
        self._hand.click(compose_tag(self._standing().alias, suffix, SUF_BUTTON))

    def _standing(self) -> WindowReading:
        window = self.window()
        if window is None:
            raise MissingPromptError(f"No prompt under '{self._tag}' stands on the screen")

        return window
