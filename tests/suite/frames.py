from typing import Final, List, Tuple

import dearpygui.dearpygui as dpg

from sampletones_shared.types.callback import VoidCallback

ONE_FRAME: Final[int] = 1


class Frames:
    """The frames a widget defers work to, carried out when a case says one was rendered.

    DearPyGui runs a frame callback from the render loop, which a suite never starts, so work a
    widget holds back until its rows are placed waits here. Holding it rather than running it as
    it arrives is what lets a case say how many frames passed: a region asking for another pass
    gets one per rendered frame, the way it would on screen, and a case reads how much work still
    stands waiting.
    """

    def __init__(self) -> None:
        self._held: List[Tuple[int, VoidCallback]] = []

    def hold(self, callback: VoidCallback, frame_count: int = ONE_FRAME) -> None:
        """Take work a widget hands over, standing in for ``FrameCallbackManager``.

        ``frame_count`` is how many frames the work waits through, which is what the manager
        counts from the frame the widget handed it over on.
        """
        self._held.append((max(ONE_FRAME, frame_count), callback))

    @property
    def pending(self) -> int:
        """How many pieces of work stand waiting on a frame."""
        return len(self._held)

    def render(self, frames: int = ONE_FRAME) -> None:
        """Carry out the work each of this many frames would, in the order it was handed over."""
        for _ in range(frames):
            counted = [(waiting - 1, callback) for waiting, callback in self._held]
            due = [callback for waiting, callback in counted if not waiting]
            self._held = [(waiting, callback) for waiting, callback in counted if waiting]
            for callback in due:
                callback()


VISIBLE_HANDLER: Final[str] = "mvAppItemType::mvVisibleHandler"


class DrawnFrames:
    """The frames a widget waiting on an item's visible handler is drawn in, rendered by a case.

    DearPyGui reports an item visible on each frame it draws it in, and a suite renders no frame, so
    a case says how many frames passed and whether the widgets stood on screen through them. Each
    frame runs every visible handler standing on, the way DearPyGui would for an item it drew.
    """

    def __init__(self) -> None:
        self.on_screen = True

    @property
    def pending(self) -> int:
        """How many visible handlers stand on, waiting for a frame their item is drawn in."""
        return len(self._watching())

    def render(self, frames: int = ONE_FRAME) -> None:
        """Run the visible handlers standing on through this many frames, where the items are drawn."""
        for _ in range(frames):
            if not self.on_screen:
                continue

            for handler in self._watching():
                dpg.get_item_callback(handler)()

    @staticmethod
    def _watching() -> List[int]:
        return [
            item
            for item in dpg.get_all_items()
            if dpg.get_item_type(item) == VISIBLE_HANDLER and dpg.get_item_configuration(item)["show"]
        ]
