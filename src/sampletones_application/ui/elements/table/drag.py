from collections.abc import Hashable
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.utils.gui.keyboard.modifiers import Modifier, capture_modifiers
from sampletones_shared.types.application import Sender

KeyT = TypeVar("KeyT", bound=Hashable)


@dataclass
class DragGesture(Generic[KeyT]):
    """The press a drag selection grows from.

    ``origin`` is the cell the button went down on, which is the end a plain drag anchors its
    selection at. ``extends`` records that the press held Shift, so the drag carries the
    selection already on the grid instead of starting a new one. ``moved`` states that the
    pointer has reached another cell, which is what tells a drag apart from a click: until it
    is set, the press is still a click and the selection is left alone.
    """

    origin: KeyT
    extends: bool
    moved: bool = False


@dataclass(frozen=True)
class DragReach(Generic[KeyT]):
    """How far a drag has carried the pointer, and which end it grew from.

    A plain drag anchors a fresh selection at ``origin`` and runs it out to ``reached``; a drag
    whose press held Shift reports ``extends``, and carries the selection already on the grid
    out to ``reached`` instead.
    """

    origin: KeyT
    reached: KeyT
    extends: bool


class DragSelection(Generic[KeyT]):
    """The gesture a grid selection is dragged out with.

    A grid hands its pointer reports here — the cell a press holds, the click that follows, the
    press that starts the next gesture — and states the reach that comes back as a selection in
    its own coordinates. The cell cache names the widget a press landed on, and ``cell_at`` reads
    the cell the pointer stands on now off the grid's geometry.
    """

    def __init__(
        self,
        *,
        cells: EditableCells[KeyT],
        cell_at: Callable[[], Optional[KeyT]],
    ) -> None:
        self._cells = cells
        self._cell_at = cell_at
        self._gesture: Optional[DragGesture[KeyT]] = None

    def hold(self, widget: Sender) -> Optional[DragReach[KeyT]]:
        """How far a held pointer has carried, once it has left the cell the press landed on.

        DearPyGui reports no hover for the cells a held pointer passes over, so the cell the drag
        has reached is read off the grid's own geometry while the held widget names where the press
        landed. A press that stays on its own cell is still a click, and the click itself is what
        places the cursor there.
        """
        if self._gesture is None:
            origin = self._cells.key(widget)
            if origin is not None:
                self._gesture = DragGesture(
                    origin=origin,
                    extends=Modifier.SHIFT in capture_modifiers(),
                )

            return None

        reached = self._cell_at()
        if reached is None or (reached == self._gesture.origin and not self._gesture.moved):
            return None

        self._gesture.moved = True
        return DragReach(
            origin=self._gesture.origin,
            reached=reached,
            extends=self._gesture.extends,
        )

    def claims_click(self) -> bool:
        """Whether the click reaching the grid ends a drag, which the drag then takes as its own.

        A drag that comes back to the cell it started from releases there, and the release reports
        a click; that click belongs to the drag, so the range dragged out stands and the gesture
        ends here.
        """
        claimed = self._gesture is not None and self._gesture.moved
        if claimed:
            self._gesture = None

        return claimed

    def clear(self) -> None:
        """Drops the gesture in hand, so the next press drags a selection out on its own."""
        self._gesture = None
