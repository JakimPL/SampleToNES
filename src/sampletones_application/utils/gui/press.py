from typing import Generic, Optional, TypeVar

import dearpygui.dearpygui as dpg

PressT = TypeVar("PressT")


class LeftPress(Generic[PressT]):
    """A left-button press that went down on a widget, with what the widget keeps while it is held.

    A widget begins the press it hears go down on it and ends it on the release DearPyGui reports.
    DearPyGui reports no release made outside the window, so a press also ends once it is read with
    the left button up. A widget reads it from a handler that runs with the button up as well, such
    as a mouse move, so a press begun elsewhere later finds nothing held.
    """

    def __init__(self) -> None:
        self._held: Optional[PressT] = None

    def begin(self, held: PressT) -> None:
        """Keeps ``held`` for the press that went down, in place of any press before it."""
        self._held = held

    def end(self) -> None:
        """Ends the press, on the release DearPyGui reports."""
        self._held = None

    def settle(self) -> None:
        """Ends the press once the left button reads up, which is a release DearPyGui never reported."""
        if self._held is not None and not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self._held = None

    def held(self) -> Optional[PressT]:
        """What the press keeps while the left button stays down, and ``None`` once it has ended."""
        self.settle()
        return self._held
