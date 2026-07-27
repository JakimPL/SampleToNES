from unittest.mock import patch

from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.modifiers import CTRL_SHIFT

MODULE = "sampletones_application.utils.gui.keyboard.event"

KEY = 65


def test_capture_carries_the_key_and_the_modifiers_held_with_it() -> None:
    with patch(f"{MODULE}.capture_modifiers", lambda: CTRL_SHIFT):
        event = KeyEvent.capture(KEY)

    assert event == KeyEvent(key=KEY, modifiers=CTRL_SHIFT)
