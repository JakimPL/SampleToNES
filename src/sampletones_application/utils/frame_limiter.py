import time
from typing import Optional


class FrameLimiter:
    """Paces the render loop to a maximum frame rate.

    Each :meth:`tick` sleeps out the time left in the current frame's budget, holding the loop to
    ``max_fps`` frames per second regardless of the monitor's refresh rate. A ``max_fps`` of zero
    leaves pacing to vsync or the hardware.
    """

    def __init__(self, max_fps: int) -> None:
        self._frame_budget: float = 1.0 / max_fps if max_fps > 0 else 0.0
        self._last_tick: Optional[float] = None

    def tick(self) -> None:
        if self._frame_budget <= 0.0:
            return

        now = time.perf_counter()
        if self._last_tick is not None:
            remaining = self._frame_budget - (now - self._last_tick)
            if remaining > 0.0:
                time.sleep(remaining)
                now += remaining

        self._last_tick = now
