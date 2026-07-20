from typing import List, Optional

import dearpygui.dearpygui as dpg

from sampletones_application.tags.general import TAG_GLOBAL_THEME_FOCUSED_BUTTON
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dialog_navigation.stop import FocusStop


class FocusRing:
    """Ordered focus stops a dialog moves keyboard focus through.

    The stop that holds focus is tracked internally and reconciled against the field or combo the
    user is actively editing, which keeps the cycle correct whether or not a focused button reports
    its focus, and lets the field being typed into keep Enter for itself.

    As focus moves onto a button the ring paints it with the focus outline theme and rebinds the
    button's own theme once focus leaves, so the button the user is on carries a visible accent
    border. Fields show their own edit caret, so the ring leaves their appearance to DearPyGui.
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
        """Moves focus by ``step`` stops, starting from the field being edited or the tracked stop,
        skipping disabled stops and wrapping around the ring."""
        active_field = self._active_field_index()
        start = active_field if active_field is not None else self._current_index
        target = self._next_enabled_index(start, step)
        if target is not None:
            self._focus(target)

    def activate_focused(self) -> None:
        """Runs the focused button's action, leaving Enter to the field or combo being edited."""
        if self._active_field_index() is not None:
            return

        stop = self._stops[self._current_index]
        if stop.activate is not None and self._is_enabled(stop):
            stop.activate()

    def _focus(self, index: int) -> None:
        self._restore_focus_outline(self._current_index)
        self._current_index = index
        dpg.focus_item(self._stops[index].focus_tag)
        self._apply_focus_outline(index)

    def _apply_focus_outline(self, index: int) -> None:
        stop = self._stops[index]
        if stop.base_theme_tag is None:
            return

        ThemeRegistry.get(TAG_GLOBAL_THEME_FOCUSED_BUTTON).bind_to_item(stop.focus_tag)

    def _restore_focus_outline(self, index: int) -> None:
        stop = self._stops[index]
        if stop.base_theme_tag is None:
            return

        ThemeRegistry.get(stop.base_theme_tag).bind_to_item(stop.focus_tag)

    def _active_field_index(self) -> Optional[int]:
        for index, stop in enumerate(self._stops):
            if stop.activate is None and dpg.is_item_active(stop.focus_tag):
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
