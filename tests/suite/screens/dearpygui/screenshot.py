from pathlib import Path
from typing import Final

import dearpygui.dearpygui as dpg

from tests.suite.screens.dearpygui.bridge import Bridge

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
