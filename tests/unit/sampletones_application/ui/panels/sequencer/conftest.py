from typing import Final, Generator

import pytest

from sampletones_application.ui.panels.sequencer.tracker import panel as tracker
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback

UNSCROLLED: Final[float] = 0.0


@pytest.fixture(autouse=True)
def immediate_frame_callbacks(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Runs a panel's deferred frame work at once, since a suite renders no frames.

    The tracker holds the playhead's mark and the cursor's move back to the frame their scroll
    lands on, which a running application reaches on its next render and a suite never does.
    Calling the work as it is handed over keeps what a panel draws observable from the call that
    asks for it, and the table it reads the scroll it was drawn with from reports a grid at rest.
    """

    def run_now(callback: VoidCallback, frame_count: int = 1) -> None:
        callback()

    def at_rest(table: Sender) -> float:
        return UNSCROLLED

    monkeypatch.setattr(tracker.FrameCallbackManager, "set_frame_callback", run_now)
    monkeypatch.setattr(tracker.dpg, "get_y_scroll", at_rest)
    yield
