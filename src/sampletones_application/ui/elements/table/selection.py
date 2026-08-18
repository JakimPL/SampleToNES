from collections.abc import Hashable
from typing import Callable, FrozenSet, Generic, Optional, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_application.ui.elements.table.cells import EditableCells
from sampletones_application.ui.elements.table.drag import DragReach, DragSelection
from sampletones_shared.types.application import Sender

KeyT = TypeVar("KeyT", bound=Hashable)


class TableSelection(Generic[KeyT]):
    """The selection a table shows, and the pointer gesture that draws it.

    A grid states which of its cells the selection covers, in whatever coordinates it selects in;
    which of them stand painted, and how far a held pointer has carried, are held here. A selected
    cell is drawn by the selectable's own selected state, which the table's theme colours, so a
    repaint reaches only the cells whose membership changed.
    """

    def __init__(
        self,
        *,
        cells: EditableCells[KeyT],
        cell_at: Callable[[], Optional[KeyT]],
        covered: Callable[[], FrozenSet[KeyT]],
    ) -> None:
        self._cells = cells
        self._covered = covered
        self._drag: DragSelection[KeyT] = DragSelection(cells=cells, cell_at=cell_at)
        self._painted: FrozenSet[KeyT] = frozenset()

    def hold(self, widget: Sender) -> Optional[DragReach[KeyT]]:
        """How far a held pointer has carried, which is what a drag grows the selection out to."""
        return self._drag.hold(widget)

    def claims_click(self, sender: Sender, key: KeyT) -> bool:
        """Whether the click on a cell ends a drag, which the drag then takes as its own.

        DearPyGui toggles a selectable as it reports the click, so the cell is released here and
        dropped from what stands painted: the repaint that follows is what states whether the cell
        belongs to the selection.
        """
        dpg.set_value(sender, False)
        self._painted -= {key}
        if not self._drag.claims_click():
            return False

        self.repaint()
        return True

    def drop_gesture(self) -> None:
        """Drops the gesture in hand, the selection standing as it is."""
        self._drag.clear()

    def repaint(self) -> None:
        """Marks the cells the selection now covers and releases the ones it has left."""
        covered = self._covered()
        for key in self._painted ^ covered:
            widget = self._cells.widget(key)
            if widget is not None:
                dpg.set_value(widget, key in covered)

        self._painted = covered

    def reset(self) -> None:
        """Forgets the selection and the gesture, which is what a rebuilt table asks for.

        The cells a selection stood on belong to the body being replaced, so the paint is forgotten
        with them and the grid states its selection onto the new cells afresh.
        """
        self._drag.clear()
        self._painted = frozenset()
