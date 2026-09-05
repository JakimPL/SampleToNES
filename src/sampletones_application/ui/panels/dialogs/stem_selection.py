from pathlib import Path
from typing import Any, Callable, Final, List, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.tabs.main.converter import ConverterLayout
from sampletones_application.tags.compose import compose_tag
from sampletones_application.tags.main import (
    PRE_MAIN_CONVERTER_CANDIDATE,
    TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS,
    TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS,
    TAG_MAIN_CONVERTER_GROUP_STEM_SELECTION,
    TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT,
    TAG_MAIN_CONVERTER_WINDOW_STEM_SELECTION,
)
from sampletones_application.ui.elements.button import GUIButton
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource

ADD_FOCUS_STOP: Final[int] = 1


class GUIStemSelectionWindow(GUIDialogWindow):
    """A modal offering the recordings gathered, with as many as a mix holds already ticked.

    A list can hold more recordings than one mix has room for, so the reader is shown everything
    gathered and picks which of it to mix: any recording is pickable, whichever ones arrived
    ticked, so swapping the eighth for the ninth is one gesture. The line above reads what stands
    picked against the room, and the mix is settled once the pick fits.
    """

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        title: str,
        message: str,
        limit_template: str,
        add_label: str,
        cancel_label: str,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._title = title
        self._message = message
        self._limit_template = limit_template
        self._add_label = add_label
        self._cancel_label = cancel_label
        self._candidates: Tuple[Path, ...] = ()
        self._room = 0
        self._footer_height = layout.stem_selection_footer

        self.on_add: Optional[Callable[[List[Path]], None]] = None

        super().__init__(
            tag=TAG_MAIN_CONVERTER_WINDOW_STEM_SELECTION,
            width=layout.stem_selection.width,
            height=layout.stem_selection.height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(self, candidates: Sequence[Path], room: int) -> None:
        """Shows the recordings found, ticking as many as the conversion still has room for."""
        self._candidates = tuple(candidates)
        self._room = room
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The candidates and the room left are seeded by :meth:`open` before the tree rebuilds."""

    def create_window(self) -> None:
        with self.dialog_window(label=self._title, on_close=None):
            dpg.add_text(self._message, wrap=self.width)
            dpg.add_text(self._limit_text(), tag=TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT)
            dpg.add_separator()
            with dpg.child_window(
                tag=TAG_MAIN_CONVERTER_GROUP_STEM_SELECTION,
                width=-1,
                height=-self._footer_height,
                border=False,
            ):
                self._create_candidate_rows()

            dpg.add_separator()
            self._create_action_buttons()

        self._install_navigation(
            [
                FocusStop.button(TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS, self.hide),
                FocusStop.button(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, self._add),
            ],
            on_escape=self.hide,
            initial_index=ADD_FOCUS_STOP,
        )

    def _create_candidate_rows(self) -> None:
        """A box per recording gathered, the first ones the mix has room for arriving ticked."""
        for index, candidate in enumerate(self._candidates):
            dpg.add_checkbox(
                label=candidate.name,
                tag=self._candidate_tag(candidate),
                default_value=index < self._room,
                callback=self._on_picked,
            )

    @table_wrapper(columns=2)
    def _create_action_buttons(self) -> None:
        GUIButton(
            tag=TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS,
            label=self._cancel_label,
            callback=self.hide,
            width=-1,
        )
        GUIButton(
            tag=TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS,
            label=self._add_label,
            callback=self._add,
            width=-1,
            enabled=self._fits,
        )

    def _limit_text(self) -> str:
        return self._limit_template.format(
            picked=len(self._selected()),
            total=len(self._candidates),
            room=self._room,
        )

    def _on_picked(self, *_args: Any, **_kwargs: Any) -> None:
        """Follow what stands picked: what the line reads, and whether the mix can be settled."""
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT, self._limit_text())
        dpg_configure_item(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, enabled=self._fits)

    @property
    def _fits(self) -> bool:
        """The pick is one a mix can be built from: at least one recording, and no more than fit."""
        picked = len(self._selected())
        return 0 < picked <= self._room

    def _selected(self) -> List[Path]:
        return [
            candidate
            for candidate in self._candidates
            if dpg.does_item_exist(self._candidate_tag(candidate)) and dpg.get_value(self._candidate_tag(candidate))
        ]

    def _add(self) -> None:
        if not self._fits:
            return

        selected = self._selected()
        self.hide()
        self.call(self.on_add, selected)

    @staticmethod
    def _candidate_tag(candidate: Path) -> str:
        return compose_tag(PRE_MAIN_CONVERTER_CANDIDATE, str(candidate))
