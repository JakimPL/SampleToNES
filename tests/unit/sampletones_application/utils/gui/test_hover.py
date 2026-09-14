from typing import List

import pytest

from sampletones_application.utils.gui.frame import FrameCallbackManager
from sampletones_application.utils.gui.hover import HOVER_RECHECK_FRAMES, HoverWatch
from tests.suite.frames import Frames

RESTING_FRAMES = 12


class Pointer:
    """Where the pointer stands, and the looks a watch painted as it read that."""

    def __init__(self) -> None:
        self.over = True
        self.painted: List[bool] = []

    def paint(self) -> bool:
        self.painted.append(self.over)
        return self.over


@pytest.fixture
def frames(monkeypatch: pytest.MonkeyPatch) -> Frames:
    held = Frames()
    monkeypatch.setattr(FrameCallbackManager, "set_frame_callback", held.hold)
    return held


class TestTheHoverAWatchHolds:
    """A hover handler reports every frame the pointer rests on an item, and the watch reads it again
    until the pointer has left."""

    def test_a_report_paints_the_hover_at_once(self, frames: Frames) -> None:
        pointer = Pointer()

        HoverWatch(pointer.paint).report()

        assert pointer.painted == [True]

    def test_a_pointer_resting_keeps_one_reading_waiting(self, frames: Frames) -> None:
        pointer = Pointer()
        watch = HoverWatch(pointer.paint)

        for _ in range(RESTING_FRAMES):
            watch.report()
            frames.render()

        assert frames.pending == 1

    def test_the_reading_waits_for_the_hover_to_end(self, frames: Frames) -> None:
        pointer = Pointer()
        HoverWatch(pointer.paint).report()
        pointer.painted.clear()

        frames.render(HOVER_RECHECK_FRAMES - 1)
        assert pointer.painted == []

        frames.render()
        assert pointer.painted == [True]

    def test_a_pointer_leaving_paints_the_idle_look_and_ends_the_watch(self, frames: Frames) -> None:
        pointer = Pointer()
        HoverWatch(pointer.paint).report()
        pointer.over = False

        frames.render(HOVER_RECHECK_FRAMES)

        assert (pointer.painted, frames.pending) == ([True, False], 0)

    def test_a_pointer_back_starts_the_watch_again(self, frames: Frames) -> None:
        pointer = Pointer()
        watch = HoverWatch(pointer.paint)
        watch.report()
        pointer.over = False
        frames.render(HOVER_RECHECK_FRAMES)
        pointer.over = True

        watch.report()

        assert (pointer.painted, frames.pending) == ([True, False, True], 1)
