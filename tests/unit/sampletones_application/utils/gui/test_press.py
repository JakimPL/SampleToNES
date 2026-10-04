from dataclasses import dataclass
from typing import Final

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.press import LeftPress

HELD: Final[str] = "held"


@dataclass
class Button:
    """Whether the left mouse button reads down."""

    down: bool = True


@pytest.fixture
def button(monkeypatch: pytest.MonkeyPatch) -> Button:
    button = Button()
    monkeypatch.setattr(dpg, "is_mouse_button_down", lambda _button: button.down)
    return button


class TestALeftPress:
    """A press stands from its beginning until its release, or until it is read with the button up."""

    def test_a_press_keeps_what_it_began_with_while_the_button_is_down(self, button: Button) -> None:
        press: LeftPress[str] = LeftPress()
        press.begin(HELD)

        assert press.held() == HELD

    def test_a_reported_release_ends_the_press(self, button: Button) -> None:
        press: LeftPress[str] = LeftPress()
        press.begin(HELD)

        press.end()

        assert press.held() is None

    def test_a_release_never_reported_ends_the_press_once_the_button_reads_up(self, button: Button) -> None:
        """A later press keeps the button down again, and finds nothing held."""
        press: LeftPress[str] = LeftPress()
        press.begin(HELD)

        button.down = False
        press.settle()
        button.down = True

        assert press.held() is None

    def test_reading_with_the_button_up_ends_the_press(self, button: Button) -> None:
        press: LeftPress[str] = LeftPress()
        press.begin(HELD)
        button.down = False

        assert press.held() is None
