import pytest

from sampletones_application.utils.gui.frame import FrameCallbackManager
from tests.suite.frames import Frames


@pytest.fixture
def frames(monkeypatch: pytest.MonkeyPatch) -> Frames:
    """The frames a stems list holds its settle back to, which a case renders for itself."""
    held = Frames()
    monkeypatch.setattr(FrameCallbackManager, "set_frame_callback", held.hold)
    return held
