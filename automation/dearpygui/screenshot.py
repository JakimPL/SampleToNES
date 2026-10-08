import threading
from collections.abc import Buffer
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List

import dearpygui.dearpygui as dpg

from automation.dearpygui.bridge import Bridge

WRITE_TIMEOUT_SECONDS: Final[float] = 10.0


def capture(bridge: Bridge, path: Path) -> Path:
    """Saves the next frame the application draws as a PNG at ``path``, and returns the path.

    DearPyGui writes the picture while drawing a frame, so the capture waits for the frame to land.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    bridge.ask(lambda: dpg.output_frame_buffer(file=str(path)))
    bridge.expect(
        lambda: bridge.ask(path.exists),
        bool,
        description=f"the screenshot {path} to be written",
        timeout=WRITE_TIMEOUT_SECONDS,
    )
    return path


@dataclass(frozen=True)
class DrawnFrame:
    """One frame as DearPyGui drew it: its size, and its pixels row after row, each red, green, blue and alpha as
    32-bit fractions.
    """

    width: int
    height: int
    pixels: bytes


def drawn_frame(bridge: Bridge) -> DrawnFrame:
    """The next frame the application draws.

    DearPyGui hands the frame over while drawing it, so the reading waits for it to land.
    """
    landed: List[DrawnFrame] = []
    taken = threading.Event()

    def take(_sender: object, frame: Buffer) -> None:
        landed.append(
            DrawnFrame(
                width=dpg.get_viewport_client_width(),
                height=dpg.get_viewport_client_height(),
                pixels=memoryview(frame).tobytes(),
            )
        )
        taken.set()

    bridge.ask(lambda: dpg.output_frame_buffer(callback=take))
    bridge.expect(
        taken.is_set,
        bool,
        description="the frame to be handed over",
        timeout=WRITE_TIMEOUT_SECONDS,
    )
    return landed[0]
