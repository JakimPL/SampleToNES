from typing import Callable, Final

from sampletones_application.utils.gui.frame import FrameCallbackManager

HOVER_RECHECK_FRAMES: Final[int] = 2


class HoverWatch:
    """Holds a hover look on items for as long as the pointer rests on them.

    DearPyGui reports a hover on every frame the pointer stands over an item and reports its leaving
    not at all, so the watch reads the hover again a couple of frames on while it lasts. Every report
    arriving meanwhile joins the reading already under way, which keeps one frame callback waiting
    however long the pointer rests.

    ``paint`` gives each watched item the look the pointer's place calls for and answers whether the
    pointer still stands over one of them, so the reading that finds it gone paints the idle look last.
    """

    def __init__(self, paint: Callable[[], bool]) -> None:
        self._paint = paint
        self._watching = False

    def report(self) -> None:
        """Take a hover handler's report, which starts the watch when none is under way."""
        if self._watching:
            return

        self._check()

    def _check(self) -> None:
        self._watching = self._paint()
        if self._watching:
            FrameCallbackManager.set_frame_callback(self._check, HOVER_RECHECK_FRAMES)
