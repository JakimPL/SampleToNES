from typing import List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop


class FocusRing:
    """Ordered focus stops a dialog moves keyboard focus through.

    The stop that holds focus is tracked internally and reconciled against the fields and combos
    that report focus reliably, which keeps the cycle correct whether or not a focused button
    reports its focus, and lets a focused field keep Enter for itself.
    """

    def __init__(
        self,
        stops: List[FocusStop],
        initial_index: int = 0,
    ) -> None:
        self._stops = stops
        self._initial_index = initial_index
        self._current_index = initial_index

    def focus_initial(self) -> None:
        """Focuses the stop the dialog opens on."""
        self._focus(self._initial_index)

    def cycle(self, step: int) -> None:
        """Moves focus by ``step`` stops, starting from a clicked field or the tracked stop,
        skipping disabled stops and wrapping around the ring."""
        focused_field = self._focused_field_index()
        start = focused_field if focused_field is not None else self._current_index
        target = self._next_enabled_index(start, step)
        if target is not None:
            self._focus(target)

    def activate_focused(self) -> None:
        """Runs the focused button's action, leaving Enter to a field or combo that holds focus."""
        if self._focused_field_index() is not None:
            return

        stop = self._stops[self._current_index]
        if stop.activate is not None and self._is_enabled(stop):
            stop.activate()

    def _focus(self, index: int) -> None:
        self._current_index = index
        dpg.focus_item(self._stops[index].focus_tag)

    def _focused_field_index(self) -> Optional[int]:
        for index, stop in enumerate(self._stops):
            if stop.activate is None and dpg.is_item_focused(stop.focus_tag):
                return index

        return None

    def _next_enabled_index(self, start: int, step: int) -> Optional[int]:
        count = len(self._stops)
        for offset in range(1, count + 1):
            index = (start + step * offset) % count
            if self._is_enabled(self._stops[index]):
                return index

        return None

    def _is_enabled(self, stop: FocusStop) -> bool:
        return bool(dpg.is_item_enabled(stop.enabled_tag))
