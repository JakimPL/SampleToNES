from typing import Final, Iterator, List
from unittest.mock import patch

import dearpygui.dearpygui as dpg
import pytest

from sampletones_application.utils.callbacks.failures import UnhandledFailures
from sampletones_application.utils.gui.frame import FrameCallbackManager

DRAWN_FRAME: Final[int] = 1


class FrameCount:
    """The frame DearPyGui reports as drawn, moved by the case alone."""

    def __init__(self) -> None:
        self.drawn = 0

    def __call__(self) -> int:
        return self.drawn


@pytest.fixture
def frame_count() -> Iterator[FrameCount]:
    """DearPyGui's frame count and frame callbacks stood in for, since a suite renders no frame."""
    count = FrameCount()
    with (
        patch.object(dpg, "get_frame_count", count),
        patch.object(dpg, "set_frame_callback"),
    ):
        yield count


class TestAFrameCallbackThatRaises:
    """A frame callback that raises is reported, and the others due in that frame still run."""

    def test_the_others_due_still_run(self, frame_count: FrameCount) -> None:
        reported: List[Exception] = []
        ran: List[str] = []
        failure = RuntimeError("the frame callback went wrong")

        def failing() -> None:
            raise failure

        UnhandledFailures.attach(reported.append, post=lambda present, exception: present(exception))
        FrameCallbackManager.set_frame_callback(failing)
        FrameCallbackManager.set_frame_callback(lambda: ran.append("after"))
        frame_count.drawn = DRAWN_FRAME

        FrameCallbackManager.process()

        assert ran == ["after"]
        assert reported == [failure]
