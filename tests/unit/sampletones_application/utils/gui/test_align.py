from typing import Final, List, Sequence, Tuple

import pytest

from sampletones_application.utils.gui import align as align_module
from sampletones_application.utils.gui.align import center_when_settled
from sampletones_application.utils.placement import centered_position
from sampletones_shared.types.callback import VoidCallback

FORM_SIZES: Final[Tuple[Tuple[int, int], ...]] = ((420, 45), (420, 217), (420, 217))
SETTLED_SIZE: Final[Tuple[int, int]] = (420, 217)
VIEWPORT: Final[Tuple[int, int]] = (1600, 1000)
WIDENING_STEP: Final[int] = 63
WINDOW_TAG: Final[str] = "settings.window"


class Window:
    """A window drawn at a stated size each frame, with the frames the pass asks for run by hand.

    A frame runs the callbacks armed for it and the readings taken during it answer with that
    frame's size, which is what lets a case state a window's whole way to its final size.
    """

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        sizes: Sequence[Tuple[int, int]],
        *,
        exists: bool = True,
    ) -> None:
        self.sizes = list(sizes)
        self.frame = 0
        self.positions: List[List[int]] = []
        self._armed: List[VoidCallback] = []
        monkeypatch.setattr(align_module.FrameCallbackManager, "set_frame_callback", self._arm)
        monkeypatch.setattr(align_module.dpg, "does_item_exist", lambda tag: exists)
        monkeypatch.setattr(align_module.dpg, "get_item_rect_size", lambda tag: self.size)
        monkeypatch.setattr(align_module.dpg, "set_item_pos", lambda tag, position: self.positions.append(position))
        monkeypatch.setattr(align_module.dpg, "get_viewport_client_width", lambda: VIEWPORT[0])
        monkeypatch.setattr(align_module.dpg, "get_viewport_client_height", lambda: VIEWPORT[1])

    @property
    def size(self) -> Tuple[int, int]:
        return self.sizes[min(self.frame, len(self.sizes) - 1)]

    @property
    def waiting(self) -> bool:
        """Whether the pass has asked for another frame."""
        return bool(self._armed)

    def _arm(self, callback: VoidCallback, frame_count: int = 1) -> None:
        self._armed.append(callback)

    def draw(self, frames: int) -> None:
        """Draws frames while the pass still asks for one."""
        for _ in range(frames):
            if not self._armed:
                return

            armed, self._armed = self._armed, []
            for callback in armed:
                callback()

            self.frame += 1


def _centered(size: Tuple[int, int]) -> List[int]:
    return list(centered_position((VIEWPORT[0] // 2, VIEWPORT[1] // 2), *size))


class TestCenteringAWindowAsItTakesItsSize:
    """A dialog stands centered from the frame it is first drawn in until it settles there."""

    def test_a_form_is_centered_against_every_size_it_is_drawn_at(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A form measures its fields on the second frame, and stands centered on both."""
        window = Window(monkeypatch, FORM_SIZES)

        center_when_settled(WINDOW_TAG)
        window.draw(len(FORM_SIZES))

        assert window.positions == [_centered(FORM_SIZES[0]), _centered(SETTLED_SIZE), _centered(SETTLED_SIZE)]

    def test_two_readings_that_agree_end_the_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A dialog can be dragged, so the pass lets go once the size it reads stops changing."""
        window = Window(monkeypatch, FORM_SIZES)

        center_when_settled(WINDOW_TAG)
        window.draw(len(FORM_SIZES) + 5)

        assert not window.waiting
        assert len(window.positions) == len(FORM_SIZES)

    def test_a_window_still_widening_is_read_again(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The keybindings list widens over a dozen frames, and is centered on each of them."""
        widening = [(620 + WIDENING_STEP * step, 647) for step in range(13)] + [(620 + WIDENING_STEP * 12, 647)]
        window = Window(monkeypatch, widening)

        center_when_settled(WINDOW_TAG)
        window.draw(len(widening))

        assert window.positions == [_centered(size) for size in widening]
        assert not window.waiting

    def test_a_window_no_longer_drawn_ends_the_pass(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A dialog closed before it settled leaves nothing to center."""
        window = Window(monkeypatch, FORM_SIZES, exists=False)

        center_when_settled(WINDOW_TAG)
        window.draw(len(FORM_SIZES))

        assert window.positions == []
        assert not window.waiting
