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


CURSOR_TARGET: Final[_Target] = _Target(region="cursor block", anchor="cursor cell")
NAMED_TARGET: Final[_Target] = _Target(region="named block", anchor="named cell")


class _Grid:
    """A grid recording what it was asked to do, in the order it was asked.

    The entry it settles and the hooks it announces through land in one list, so a test reads
    both what a gesture reached and when the grid committed what was being typed.
    """

    def __init__(
        self,
        *,
        target: Optional[_Target] = None,
        can_paste: bool = True,
    ) -> None:
        self.events: List[str] = []
        self._target = target
        self.on_copy_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"copy {region}")
        self.on_cut_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"cut {region}")
        self.on_delete_block: Optional[Callable[[str], None]] = lambda region: self.events.append(f"delete {region}")
        self.on_paste_block: Optional[Callable[[str], None]] = lambda cell: self.events.append(f"paste {cell}")
        self.can_paste_block: Optional[Callable[[], bool]] = lambda: can_paste

    def commit_entry(self) -> None:
        self.events.append("commit")

    def cursor_target(self) -> Optional[_Target]:
        return self._target


@dataclass(frozen=True)
class GestureCase:
    """One of the four gestures, raised at the cursor and on a target a menu named."""

    name: str
    at_cursor: Callable[[Gestures], None]
    at_target: Callable[[Gestures, _Target], None]
    from_cursor: str
    from_target: str


CASES: Final[Tuple[GestureCase, ...]] = (
    GestureCase(
        name="copy",
        at_cursor=lambda gestures: gestures.copy(),
        at_target=lambda gestures, target: gestures.copy_at(target),
        from_cursor="copy cursor block",
        from_target="copy named block",
    ),
    GestureCase(
        name="cut",
        at_cursor=lambda gestures: gestures.cut(),
        at_target=lambda gestures, target: gestures.cut_at(target),
        from_cursor="cut cursor block",
        from_target="cut named block",
    ),
    GestureCase(
        name="delete",
        at_cursor=lambda gestures: gestures.delete(),
        at_target=lambda gestures, target: gestures.delete_at(target),
        from_cursor="delete cursor block",
        from_target="delete named block",
    ),
    GestureCase(
        name="paste",
        at_cursor=lambda gestures: gestures.paste(),
        at_target=lambda gestures, target: gestures.paste_at(target),
        from_cursor="paste cursor cell",
        from_target="paste named cell",
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
class TestAtTheCursor:
    """A key press acts on the target the cursor names, once the entry being typed has landed."""

    def test_a_gesture_reaches_the_cursor_s_own_target(self, case: GestureCase) -> None:
        grid = _Grid(target=CURSOR_TARGET)

        case.at_cursor(BlockGestures(grid=grid))

        assert grid.events == ["commit", case.from_cursor]

    def test_a_grid_holding_no_cursor_settles_its_entry_and_stands(self, case: GestureCase) -> None:
        grid = _Grid(target=None)

        case.at_cursor(BlockGestures(grid=grid))

        assert grid.events == ["commit"]


@pytest.mark.parametrize("case", CASES, ids=[case.name for case in CASES])
class TestOnANamedTarget:
    """A menu item acts on the target it was built for, wherever the cursor happens to stand."""

    def test_a_gesture_reaches_the_target_it_was_handed(self, case: GestureCase) -> None:
        grid = _Grid(target=CURSOR_TARGET)

        case.at_target(BlockGestures(grid=grid), NAMED_TARGET)

        assert grid.events == [case.from_target]


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
