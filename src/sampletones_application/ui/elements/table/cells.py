from collections.abc import Hashable
from typing import Callable, Dict, Generic, Optional, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_shared.constants.symbols import DOT
from sampletones_shared.types.application import Sender

KeyT = TypeVar("KeyT", bound=Hashable)


def pending_label(pending: str, stored: str, width: int) -> str:
    """Label for the cell currently under the edit cursor.

    Returns the committed ``stored`` value until the user types, then the entered
    digits padded with dots up to ``width``. The caret position is drawn over the
    label by
    :class:`~sampletones_application.ui.elements.table.caret.CaretOverlay`.
    """
    if not pending:
        return stored

    return pending + DOT * (width - len(pending))


class EditableCells(Generic[KeyT]):
    """Keyed cache of editable table cells with incremental diff redraw.

    Owns the mapping from a cell key to its DearPyGui widget and to the label
    currently shown, so a panel can reconfigure only the cells whose value changed,
    leaving the rest of the table in place. The panel builds the widgets
    (registering each via :meth:`register`) and supplies a ``render`` callback that
    turns a key into its label, factoring in cursor/pending state.
    """

    def __init__(self) -> None:
        self._widgets: Dict[KeyT, Sender] = {}
        self._values: Dict[KeyT, str] = {}

    @property
    def values(self) -> Dict[KeyT, str]:
        return self._values

    def reset(self, values: Dict[KeyT, str]) -> None:
        """Drops the widget references and reseeds the value cache for a rebuild."""
        self._widgets = {}
        self._values = dict(values)

    def register(self, key: KeyT, widget: Sender) -> None:
        self._widgets[key] = widget

    def widget(self, key: KeyT) -> Optional[Sender]:
        return self._widgets.get(key)

    def reconcile(self, values: Dict[KeyT, str], render: Callable[[KeyT], str]) -> None:
        """Updates only the cells whose label changed since the last reconcile."""
        for key, value in values.items():
            if self._values.get(key) == value:
                continue

            self._values[key] = value
            widget = self._widgets.get(key)
            if widget is not None:
                dpg.configure_item(widget, label=render(key))
