from typing import Optional, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.general import SUF_HANDLER_REGISTRY
from sampletones_application.utils.gui.dpg import dpg_append_items, dpg_delete_item
from sampletones_shared.types.application import Sender
from sampletones_shared.types.callback import VoidCallback


class MenuSection:
    """A run of items a menu states afresh each time a reader opens it.

    A menu bar is built once, while what its items should say follows the cursor and the selection
    at the moment the menu is opened. A section keeps a marker inside the menu it belongs to: the
    framework reports that marker drawn once a frame while the menu stands open, so a gap in those
    reports names a fresh opening, and the section takes its standing items away and states them
    again. The items stay between openings, which gives the popup its full height on the frame it
    appears, and the rebuilt ones take over a frame later — long before an item can be reached.

    The marker leads the menu, holding nothing: a container standing below a menu item takes the
    width those items span as its own, which the popup then grows to fit on every frame it stays
    open.
    """

    def __init__(
        self,
        *,
        menu_tag: str,
        marker_tag: str,
        build: VoidCallback,
    ) -> None:
        self._menu_tag = menu_tag
        self._marker_tag = marker_tag
        self._build = build
        self._handler_tag = compose_tag(marker_tag, SUF_HANDLER_REGISTRY)
        self._drawn_frame: Optional[int] = None
        self._items: Tuple[Sender, ...] = ()

    def add_marker(self) -> None:
        """States the marker the section is reported by, inside the menu being built."""
        dpg.add_group(tag=self._marker_tag)

    def watch(self) -> None:
        """Reports the marker drawn from here on, and states the section once."""
        with dpg.item_handler_registry(tag=self._handler_tag):
            dpg.add_item_visible_handler(callback=self._on_marker_drawn)

        dpg.bind_item_handler_registry(self._marker_tag, self._handler_tag)
        self.refresh()

    def refresh(self) -> None:
        """Takes the standing items away and asks for the section as it reads now.

        Only what the last build stated is taken away, so the items the menu declares for itself
        stand where they are.
        """
        for item in self._items:
            dpg_delete_item(item)

        self._items = dpg_append_items(self._menu_tag, self._build)

    def _on_marker_drawn(
        self,
        _sender: Sender,
        _app_data: Sender,
    ) -> None:
        frame = dpg.get_frame_count()
        reopened = self._drawn_frame is None or frame - self._drawn_frame > 1
        self._drawn_frame = frame
        if reopened:
            self.refresh()
