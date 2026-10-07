from dataclasses import dataclass
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import dearpygui.dearpygui as dpg

from sampletones_application.layout.tabs.sequencer import SequencerLayout
from sampletones_application.tags.sequencer import TAG_SEQUENCER_TRACKER_TABLE
from sampletones_application.ui.elements.fonts.font import Font
from sampletones_application.ui.elements.fonts.registry import FontRegistry
from sampletones_application.ui.panels.sequencer.display import row_kinds, row_values
from sampletones_application.ui.panels.sequencer.rows import group_color
from sampletones_application.ui.panels.sequencer.tracker.band import TrackerRows
from sampletones_application.ui.panels.sequencer.tracker.row import (
    add_empty_cell,
    add_slot_group,
    slot_font,
)
from sampletones_application.ui.panels.sequencer.tracker.themes import TrackerThemes
from sampletones_application.utils.palette.colors.base import BaseColor
from sampletones_application.utils.palette.colors.faded import FadedColor
from sampletones_application.utils.palette.colors.layered import LayeredColor
from sampletones_application.view_model.sequencer.settings import SequencerSettingsViewModel
from sampletones_application.view_model.sequencer.slot import TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import SequencerContextRowViewModel
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id
from sampletones_shared.types.application import Sender

BLANK_LABEL: Final[str] = ""

SongRow = Tuple[int, int]
Entries = Sequence[SequencerContextRowViewModel]
Placed = List[Optional[SequencerContextRowViewModel]]


@dataclass
class _StandingRow:
    """A table row standing beyond the frame: the widgets it draws through and the song row it shows."""

    number: Sender
    slots: Dict[TrackerSlot, Sender]
    entry: Optional[SequencerContextRowViewModel]


class ContextRows:
    """The rows of the song standing before and after the shown frame, drawn dimmed and read-only.

    The tracker centers the row it follows, so the table holds as many rows on each side of the
    frame as stand above the band's center. They show the song's neighboring rows, each read as
    its own frame reads it, and where the song ends they stand blank, so the room is there whatever
    frame is shown. Every cell wears a label theme and carries no gesture: a row of another frame
    is edited by showing that frame.

    A background follows the beat and bar grouping by the row's own index, dimmed as its text is,
    and the playhead's mark stands on a row here while playback sounds it.
    """

    def __init__(
        self,
        *,
        layout: SequencerLayout,
        themes: TrackerThemes,
        subcolumn_widths: Mapping[SubColumn, int],
    ) -> None:
        self._layout = layout
        self._themes = themes
        self._subcolumn_widths = subcolumn_widths
        self._lead: List[_StandingRow] = []
        self._trail: List[_StandingRow] = []

    def build_lead(self, reach: int, entries: Entries) -> None:
        """Appends the rows standing before the frame to the table, the song's nearest last."""
        self._lead = [self._build_row(entry) for entry in self._placed_before(reach, entries)]

    def build_trail(self, reach: int, entries: Entries) -> None:
        """Appends the rows standing after the frame to the table, the song's nearest first."""
        self._trail = [self._build_row(entry) for entry in self._placed_after(reach, entries)]

    def fill(self, lead: Entries, trail: Entries) -> None:
        """Shows the song rows now standing either side of the frame, rewriting the rows that changed."""
        for row, entry in zip(self._lead, self._placed_before(len(self._lead), lead)):
            self._show(row, entry)

        for row, entry in zip(self._trail, self._placed_after(len(self._trail), trail)):
            self._show(row, entry)

    def paint(
        self,
        rows: TrackerRows,
        settings: SequencerSettingsViewModel,
        playing: Optional[SongRow],
    ) -> None:
        """Gives every row either side of the frame its background, the playhead's mark among them.

        Args:
            rows: Where the table's rows stand.
            settings: The meter the grouping is counted by.
            playing: The frame and row playback sounds, or ``None`` while nothing plays.
        """
        for slot, row in enumerate(self._lead):
            self._draw(rows.lead_table_row(slot), self._background(row.entry, settings, playing))

        for slot, row in enumerate(self._trail):
            self._draw(rows.trail_table_row(slot), self._background(row.entry, settings, playing))

    @staticmethod
    def _placed_before(reach: int, entries: Entries) -> Placed:
        """The song row each of ``reach`` rows above the frame shows, blank above where the song begins."""
        taken: Placed = list(entries[max(0, len(entries) - reach) :])
        return [None] * (reach - len(taken)) + taken

    @staticmethod
    def _placed_after(reach: int, entries: Entries) -> Placed:
        """The song row each of ``reach`` rows below the frame shows, blank below where the song ends."""
        taken: Placed = list(entries[:reach])
        return taken + [None] * (reach - len(taken))

    def _build_row(self, entry: Optional[SequencerContextRowViewModel]) -> _StandingRow:
        """Appends one row to the table, laid out cell for cell as a row of the frame is."""
        row_id = dpg.add_table_row(parent=TAG_SEQUENCER_TRACKER_TABLE)
        add_empty_cell(row_id)
        number = self._add_number(row_id)
        slots: Dict[TrackerSlot, Sender] = {}
        self._add_column(row_id, None, slots)
        add_empty_cell(row_id)
        for channel in ChannelName.items():
            self._add_column(row_id, channel, slots)

        row = _StandingRow(number=number, slots=slots, entry=None)
        self._show(row, entry)
        return row

    def _add_number(self, row_id: Sender) -> Sender:
        cell = dpg.add_table_cell(parent=row_id)
        number: Sender = dpg.add_selectable(
            parent=cell,
            label=BLANK_LABEL,
            height=self._layout.tracker.row_height,
        )
        FontRegistry.bind_to_item(number, Font.MONO_SMALL)
        dpg.bind_item_theme(number, self._themes.context_row_number)
        return number

    def _add_column(
        self,
        row_id: Sender,
        channel: Optional[ChannelName],
        slots: Dict[TrackerSlot, Sender],
    ) -> None:
        group = add_slot_group(row_id)
        for subcolumn in SubColumn:
            selectable = dpg.add_selectable(
                parent=group,
                label=BLANK_LABEL,
                width=self._subcolumn_widths[subcolumn],
                height=self._layout.tracker.row_height,
            )
            FontRegistry.bind_to_item(selectable, slot_font(channel))
            dpg.bind_item_theme(selectable, self._themes.context_cell(subcolumn, None))
            slots[TrackerSlot(channel, subcolumn)] = selectable

    def _show(self, row: _StandingRow, entry: Optional[SequencerContextRowViewModel]) -> None:
        """Rewrites a row to read as the song row it now stands for, or blank beyond the song."""
        if entry == row.entry:
            return

        row.entry = entry
        dpg.configure_item(row.number, label=display_id(entry.row.index) if entry is not None else BLANK_LABEL)
        values = row_values(entry.row) if entry is not None else {}
        kinds = row_kinds(entry.row) if entry is not None else {}
        for slot, selectable in row.slots.items():
            dpg.configure_item(selectable, label=values.get(slot, BLANK_LABEL))
            dpg.bind_item_theme(selectable, self._themes.context_cell(slot.subcolumn, kinds.get(slot)))

    def _background(
        self,
        entry: Optional[SequencerContextRowViewModel],
        settings: SequencerSettingsViewModel,
        playing: Optional[SongRow],
    ) -> Optional[BaseColor]:
        """The shade a row beside the frame carries: its group dimmed, and the mark while it sounds."""
        if entry is None:
            return None

        colors = self._layout.colors
        group = group_color(entry.row.index, settings, colors)
        dimmed = (
            FadedColor(color=group, fraction=self._layout.tracker.muted_text_fraction) if group is not None else None
        )
        if playing != (entry.frame_index, entry.row.index):
            return dimmed

        if dimmed is None:
            return colors.playback_row

        return LayeredColor(base=dimmed, overlay=colors.playback_row)

    @staticmethod
    def _draw(table_row: int, color: Optional[BaseColor]) -> None:
        if color is None:
            dpg.unhighlight_table_row(TAG_SEQUENCER_TRACKER_TABLE, table_row)
        else:
            dpg.highlight_table_row(TAG_SEQUENCER_TRACKER_TABLE, table_row, color=color.rgba)
