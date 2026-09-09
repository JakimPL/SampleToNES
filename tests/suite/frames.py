from typing import Final, List

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
        self._held: List[VoidCallback] = []

    def hold(self, callback: VoidCallback, frame_count: int = ONE_FRAME) -> None:
        """Take work a widget hands over, standing in for ``FrameCallbackManager``."""
        self._held.append(callback)

    @property
    def pending(self) -> int:
        """How many pieces of work stand waiting on a frame."""
        return len(self._held)

    def render(self, frames: int = ONE_FRAME) -> None:
        """Carry out the work each of this many frames would, in the order it was handed over."""
        for _ in range(frames):
            held, self._held = self._held, []
            for callback in held:
                callback()
