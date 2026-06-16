from collections.abc import Hashable
from typing import Callable, Dict, Generic, Optional, TypeVar

import dearpygui.dearpygui as dpg

from sampletones_shared.constants.symbols import DOT, UNDERSCORE
from sampletones_shared.types.application import Sender

KeyT = TypeVar("KeyT", bound=Hashable)


def active_label(pending: str, width: int) -> str:
    remaining = width - len(pending)
    if remaining == 0:
        return pending
    return pending + UNDERSCORE + DOT * (remaining - 1)


class EditableCells(Generic[KeyT]):
    """Keyed cache of editable table cells with incremental diff redraw.

    Owns the mapping from a cell key to its DearPyGui widget and to the label
    currently shown, so a panel can reconfigure only the cells whose value changed
    instead of tearing down and rebuilding the table. The panel builds the widgets
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
