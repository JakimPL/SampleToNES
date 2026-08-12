from dataclasses import dataclass
from typing import Callable, Final, List, Optional, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.grid.gestures import BlockGestures

Gestures = BlockGestures[str, str]


@dataclass(frozen=True)
class _Target:
    """A block and the cell a paste lands at, written as the words each hook reports."""

    region: str
    anchor: str


NAMED_TARGET: Final[_Target] = _Target(region="named block", anchor="named cell")


class _Grid:
    """A grid recording the hooks it announced through, in the order it announced them."""

    def __init__(self, *, can_paste: bool = True) -> None:
        self.events: List[str] = []
        self.on_copy_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"copy {region}")
        self.on_cut_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"cut {region}")
        self.on_delete_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"delete {region}")
        self.on_paste_block: Optional[Callable[[str], None]] = lambda cell: self.events.append(f"paste {cell}")
        self.can_paste_block: Optional[Callable[[], bool]] = lambda: can_paste


@dataclass(frozen=True)
class GestureCase:
    """One of the four gestures, raised on the target its door named."""

    name: str
    at_target: Callable[[Gestures, _Target], None]
    reaches: str


CASES: Final[Tuple[GestureCase, ...]] = (
    GestureCase(
        name="copy",
        at_target=lambda gestures, target: gestures.copy_at(target),
        reaches="copy named block",
    ),
    GestureCase(
        name="cut",
        at_target=lambda gestures, target: gestures.cut_at(target),
        reaches="cut named block",
    ),
    GestureCase(
        name="delete",
        at_target=lambda gestures, target: gestures.delete_at(target),
        reaches="delete named block",
    ),
    GestureCase(
        name="paste",
        at_target=lambda gestures, target: gestures.paste_at(target),
        reaches="paste named cell",
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
class TestOnANamedTarget:
    """Each door names the target it acts on, and the gesture reaches exactly that block."""

    def test_a_gesture_reaches_the_target_it_was_handed(self, case: GestureCase) -> None:
        grid = _Grid()

        case.at_target(BlockGestures(grid=grid), NAMED_TARGET)

        assert grid.events == [case.reaches]


class TestPasteEnablement:
    """Paste is offered while a block stands ready for it to write."""

    def test_a_grid_holding_a_block_offers_the_paste(self) -> None:
        assert BlockGestures(grid=_Grid(can_paste=True)).can_paste() is True

    def test_a_grid_holding_none_offers_no_paste(self) -> None:
        assert BlockGestures(grid=_Grid(can_paste=False)).can_paste() is False

    def test_a_grid_awaiting_its_wiring_offers_no_paste(self) -> None:
        grid = _Grid()
        grid.can_paste_block = None

        assert BlockGestures(grid=grid).can_paste() is False
