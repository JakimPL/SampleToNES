from typing import Generator

import pytest

from sampletones_application.ui.panels.sequencer import tracker
from sampletones_shared.types.callback import VoidCallback


@pytest.fixture(autouse=True)
def immediate_frame_callbacks(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Runs a panel's deferred frame work at once, since a suite renders no frames.

    The tracker holds the playhead's mark back to the frame its scroll lands on, which a running
    application reaches on its next render and a suite never does. Calling the work as it is
    handed over keeps what a panel draws observable from the call that asks for it.
    """

    def run_now(callback: VoidCallback, frame_count: int = 1) -> None:
        callback()

    monkeypatch.setattr(tracker.FrameCallbackManager, "set_frame_callback", run_now)
    yield
