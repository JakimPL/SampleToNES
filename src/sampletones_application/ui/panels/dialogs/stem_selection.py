from pathlib import Path
from typing import Any, Callable, Final, FrozenSet, List, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.categories.manager import LanguageManager
from sampletones_application.layout.general.stems import StemsListLayout
from sampletones_application.layout.glyphs.common import CommonGlyphs
from sampletones_application.layout.tabs.main.converter import ConverterLayout
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
from sampletones_application.ui.elements.status import GUIStatusBar
from sampletones_application.ui.elements.stems.list import GUIStemsList
from sampletones_application.ui.elements.stems.offer import PICKED_SOURCES
from sampletones_application.utils.gui.align import table_wrapper
from sampletones_application.utils.gui.dialog_navigation import FocusStop
from sampletones_application.utils.gui.dpg import dpg_configure_item, dpg_set_value
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_application.view_model.shared.stems import (
    StemRowViewModel,
    StemsListViewModel,
)

Answer = Callable[[List[Path]], None]

ADD_FOCUS_STOP: Final[int] = 1
NO_PICK: Final[int] = 0


class GUIStemSelectionWindow(GUIDialogWindow):
    """The question of which recordings a mix is built from, drawn the way the converter's list is.

    A mix reaches a fixed number of recordings, so a longer list is put to the reader as the same
    rows the card shows — folders standing as folders, opening onto what they hold, each row
    picked by the box beside it. As many as the mix has room for arrive picked, and any row moves,
    so swapping the eighth for the ninth is a click each. The line above reads what stands picked
    against the room, and the mix is settled once the pick fits.

    One layout answers both places a mix runs out of room: turning the output switch on a longer
    list, and gathering a folder that overflows what is left. Both put the same question — which
    recordings the mix is built from — so a folder is offered beside what the mix already stands
    on and the answer names the whole of it.
    """

    def __init__(
        self,
        *,
        layout: ConverterLayout,
        stems_layout: StemsListLayout,
        glyphs: CommonGlyphs,
        language_manager: LanguageManager,
        status_bar: GUIStatusBar,
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
        self._footer_height = layout.stem_selection_footer
        self._rows: Tuple[StemRowViewModel, ...] = ()
        self._picked: FrozenSet[str] = frozenset()
        self._room = 0
        self._list = GUIStemsList(
            prefix=PRE_MAIN_CONVERTER_CANDIDATE,
            layout=stems_layout,
            ceiling=layout.stem_selection_list,
            glyphs=glyphs,
            language_manager=language_manager,
            status_bar=status_bar,
            offer=PICKED_SOURCES,
        )
        self._list.on_row_picked = self._on_picked

        self._answer: Optional[Answer] = None

        super().__init__(
            tag=TAG_MAIN_CONVERTER_WINDOW_STEM_SELECTION,
            width=layout.stem_selection.width,
            height=layout.stem_selection.height,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(
        self,
        rows: Sequence[StemRowViewModel],
        room: int,
        answer: Answer,
    ) -> None:
        """Shows the rows offered, picking as many recordings as the mix has room for.

        ``answer`` is what the pick reaches, which is the question this opening puts.
        """
        self._rows = tuple(rows)
        self._room = room
        self._answer = answer
        self._picked = frozenset(recording.key for recording in self._view().recordings[:room])
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The rows and the room left are seeded by :meth:`open` before the tree rebuilds."""

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
                self._list.create(TAG_MAIN_CONVERTER_GROUP_STEM_SELECTION)

            dpg.add_separator()
            self._create_action_buttons()

        self._render()
        self._install_navigation(
            [
                FocusStop.button(TAG_MAIN_CONVERTER_BUTTON_CANCEL_STEMS, self.hide),
                FocusStop.button(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, self._add),
            ],
            on_escape=self.hide,
            initial_index=ADD_FOCUS_STOP,
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

    def _view(self) -> StemsListViewModel:
        """The rows as the question draws them: one plain run, with what stands picked."""
        return StemsListViewModel(
            rows=self._rows,
            channels_in_play=(),
            muted_channels=frozenset(),
            picked_keys=self._picked,
            picking_room=self._room,
            live=True,
            collapse_levels=True,
            selected_key=None,
        )

    def _render(self) -> None:
        """Draw what stands picked: the rows, the line counting them, and whether the mix fits."""
        self._list.update_view(self._view())
        dpg_set_value(TAG_MAIN_CONVERTER_TEXT_STEM_SELECTION_LIMIT, self._limit_text())
        dpg_configure_item(TAG_MAIN_CONVERTER_BUTTON_ADD_STEMS, enabled=self._fits)

    def _limit_text(self) -> str:
        return self._limit_template.format(
            picked=len(self._picked),
            total=len(self._view().recordings),
            room=self._room,
        )

    def _on_picked(self, key: str) -> None:
        """Picks the recordings a row stands for, or lets them go where they all stand picked.

        A mix is built from a fixed number of recordings, so a row takes as many as the room left
        reaches and a full pick waits for something to leave.
        """
        view_model = self._view()
        row = view_model.row(key)
        if row is None:
            return

        self._picked = view_model.picking_settled(row)
        self._render()

    @property
    def _fits(self) -> bool:
        """The pick is one a mix can be built from: at least one recording, and no more than fit."""
        return NO_PICK < len(self._picked) <= self._room

    def _add(self) -> None:
        if not self._fits:
            return

        picked = list(self._view().picked_paths)
        self.hide()
        self.call(self._answer, picked)
