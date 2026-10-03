from tests.suite.screens.dearpygui.gestures.keyboard import Keyboard
from tests.suite.screens.dearpygui.gestures.scrolling import Scrolling
from tests.suite.screens.dearpygui.items.types import Item
from tests.suite.screens.dearpygui.keys import IMGUI_BACKSPACE, IMGUI_LEFT_CTRL, IMGUI_LETTER_A


class Hand(Scrolling, Keyboard):
    """A user's hand on the application: the pointer and the keyboard of the scenario's display.

    A gesture first reads where its control stands, refusing one beyond a user's reach, and then
    plays the events a person makes. Every step waits whole frames, since the application reads
    input once a frame: the pointer rests over a control before pressing it, and a modifier is held
    a frame before the key it modifies goes down. A gesture that closes the application ends where
    the application stopped, which is how a scenario presses the button that leaves it.

    A gesture confirms that it arrived. The control reports the pointer resting on it before a
    button goes down, and the application reports every held button and named key down while it is
    held, so a press lost on the way fails where it was lost, and a scenario expecting nothing to
    happen learns that its gesture was made.

    The pieces are `Arrival` (waiting and confirming), `Pointer` (presses and drags), `Scrolling`
    (the wheel and the scrollbars) and `Keyboard` (keys and typed text).
    """

    def replace_text(
        self,
        item: Item,
        text: str,
    ) -> None:
        """Clicks the field ``item``, selects what it holds, deletes it, and types ``text`` in its place."""
        self.click(item)
        self.press_key(IMGUI_LETTER_A, modifiers=[IMGUI_LEFT_CTRL])
        self.press_key(IMGUI_BACKSPACE, modifiers=[])
        self.type_text(text)
