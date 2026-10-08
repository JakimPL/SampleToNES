from automation.dearpygui.bridge import Bridge
from automation.dearpygui.hand import Hand
from automation.views.prompts import Prompt


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
        self.prompt = Prompt(bridge, hand, tag)

    def is_shown(self) -> bool:
        """Whether a notice of this kind stands on the screen."""
        return self.prompt.is_shown()

    def words(self) -> str:
        """Everything the notice says, its lines joined by spaces.

        Raises:
            MissingPromptError: If no notice of this kind stands on the screen.
        """
        return self.prompt.words()

    def dismiss(self) -> None:
        """Presses OK."""
        self.prompt.confirm()
