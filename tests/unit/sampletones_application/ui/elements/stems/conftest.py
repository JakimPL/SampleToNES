import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.gui.frame import FrameCallbackManager
from tests.suite.frames import Frames


@pytest.fixture
def frames(monkeypatch: pytest.MonkeyPatch) -> Frames:
    """The frames a stems list holds its settle back to, which a case renders for itself.

    A frame a case renders is one the list stood on screen in, the way a list a reader is looking
    at is drawn, so a case standing a list away says so for the frames it renders.
    """
    held = Frames()
    monkeypatch.setattr(FrameCallbackManager, "set_frame_callback", held.hold)
    monkeypatch.setattr(dpg, "is_item_visible", lambda _item: True)
    return held
