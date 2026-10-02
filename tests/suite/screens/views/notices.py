from typing import Tuple

from tests.suite.screens.dearpygui.bridge import Bridge
from tests.suite.screens.dearpygui.hand import Hand
from tests.suite.screens.dearpygui.items import read_shown_texts
from tests.suite.screens.views.prompts import MissingPromptError, Prompt


class Notice:
    """A dialog telling the reader something, such as a failure, which the reader acknowledges with OK.

    Each kind of notice composes its windows under a tag of its own, which is the one the view is
    given.
    """

    def __init__(
        self,
        bridge: Bridge,
        hand: Hand,
        tag: str,
    ) -> None:
        self._bridge = bridge
        self.prompt = Prompt(bridge, hand, tag)

    def is_shown(self) -> bool:
        return self.prompt.is_shown()

    def words(self) -> str:
        """Everything the notice says, its lines joined by spaces.

        Raises:
            MissingPromptError: If no notice of this kind stands on the screen.
        """
        window = self.prompt.window()
        if window is None:
            raise MissingPromptError("No notice of this kind stands on the screen")

        texts: Tuple[str, ...] = self._bridge.ask(lambda: read_shown_texts(window.alias))
        return " ".join(texts)

    def dismiss(self) -> None:
        """Presses OK."""
        self.prompt.confirm()
