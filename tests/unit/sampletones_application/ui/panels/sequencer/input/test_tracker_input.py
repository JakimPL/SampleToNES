from typing import Optional

from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.view_model.sequencer.slot import SLOT_COUNT, TrackerSlot
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName

ROW_COUNT = 64


def _state(
    subcolumn: SubColumn,
    *,
    row: int = 0,
    channel: Optional[ChannelName] = ChannelName.PULSE1,
    pending: str = "",
) -> TrackerInputState:
    return TrackerInputState(cursor=TrackerCursor(row, channel, subcolumn), pending=pending)


class TestNoteOffEntry:
    def test_minus_in_instrument_emits_note_off(self) -> None:
        state, action = _state(SubColumn.INSTRUMENT).type_char("-")
        assert action is not None
        assert action.note_off is True
        assert action.row == 0
        assert action.channel == ChannelName.PULSE1
        assert state.pending == ""

    def test_plus_in_instrument_is_ignored(self) -> None:
        state = _state(SubColumn.INSTRUMENT)
        new_state, action = state.type_char("+")
        assert action is None
        assert new_state is state

    def test_minus_in_transpose_is_a_sign_not_note_off(self) -> None:
        new_state, action = _state(SubColumn.TRANSPOSE).type_char("-")
        assert action is None
        assert new_state.pending.startswith("-")


class TestSelection:
    """Shift-extended moves grow a region from the cell the selection was started on."""

    def test_a_state_without_an_anchor_covers_no_region(self) -> None:
        assert _state(SubColumn.INSTRUMENT).region is None

    def test_the_first_extend_anchors_the_cell_it_came_from(self) -> None:
        extended = _state(SubColumn.INSTRUMENT, row=4).extend_row(1, ROW_COUNT)

        region = extended.region
        assert region is not None
        assert (region.first_row, region.last_row) == (4, 5)

    def test_extending_upwards_names_the_same_region_as_downwards(self) -> None:
        """The bounds are ordered by the region, so the direction of the drag leaves no trace."""
        upwards = _state(SubColumn.INSTRUMENT, row=5).extend_row(-1, ROW_COUNT).region
        downwards = _state(SubColumn.INSTRUMENT, row=4).extend_row(1, ROW_COUNT).region

        assert upwards == downwards

    def test_a_further_extend_keeps_the_original_anchor(self) -> None:
        extended = _state(SubColumn.INSTRUMENT, row=4).extend_row(1, ROW_COUNT).extend_row(3, ROW_COUNT)

        region = extended.region
        assert region is not None
        assert (region.first_row, region.last_row) == (4, 8)

    def test_extending_slots_reaches_across_the_column_boundary(self) -> None:
        extended = _state(SubColumn.VOLUME, channel=None).extend_slot(1)

        region = extended.region
        assert region is not None
        assert (region.first_slot, region.last_slot) == (2, 3)
        assert extended.cursor is not None
        assert extended.cursor.channel is ChannelName.PULSE1
        assert extended.cursor.subcolumn is SubColumn.INSTRUMENT

    def test_extending_slots_stops_at_either_end_of_the_axis(self) -> None:
        """A selection covers a run of the grid, so its reach stops where plain navigation wraps."""
        first = _state(SubColumn.INSTRUMENT, channel=None).extend_slot(-1)
        last = _state(SubColumn.VOLUME, channel=ChannelName.NOISE).extend_slot(1)

        assert first.cursor == TrackerCursor(0, None, SubColumn.INSTRUMENT)
        assert last.cursor == TrackerCursor(0, ChannelName.NOISE, SubColumn.VOLUME)

    def test_a_plain_move_collapses_the_selection(self) -> None:
        moved = _state(SubColumn.INSTRUMENT, row=4).extend_row(2, ROW_COUNT).navigate_row(1, ROW_COUNT)

        assert moved.anchor is None
        assert moved.region is None

    def test_a_plain_column_move_collapses_the_selection(self) -> None:
        moved = _state(SubColumn.INSTRUMENT).extend_row(2, ROW_COUNT).navigate_column_by(1)

        assert moved.region is None

    def test_dropping_a_partial_entry_holds_the_selection(self) -> None:
        """Every move commits what was typed first, the extending ones included."""
        held = _state(SubColumn.VOLUME, pending="5").extend_row(1, ROW_COUNT).reset_pending()

        assert held.region is not None

    def test_typing_a_value_collapses_the_selection(self) -> None:
        selected = _state(SubColumn.VOLUME, row=4).extend_row(2, ROW_COUNT)

        typed, action = selected.type_char("7")

        assert action is not None
        assert typed.region is None

    def test_a_note_off_collapses_the_selection(self) -> None:
        selected = _state(SubColumn.INSTRUMENT, row=4).extend_row(2, ROW_COUNT)

        typed, action = selected.type_char("-")

        assert action is not None
        assert action.note_off is True
        assert typed.region is None

    def test_cancel_drops_the_selection_and_the_partial_entry(self) -> None:
        cancelled = _state(SubColumn.VOLUME, pending="5").extend_row(1, ROW_COUNT).cancel()

        assert cancelled.region is None
        assert cancelled.pending == ""

    def test_collapse_keeps_the_cursor_where_it_stands(self) -> None:
        selected = _state(SubColumn.TRANSPOSE, row=4).extend_row(2, ROW_COUNT)

        collapsed = selected.collapse()

        assert collapsed.cursor == selected.cursor
        assert collapsed.region is None


class TestTargetRegion:
    """The region a block gesture acts on, which is the selection wherever one has been made."""

    def test_a_cell_of_a_grid_with_nothing_selected_is_raised_on_itself(self) -> None:
        cell = TrackerCursor(4, ChannelName.PULSE1, SubColumn.TRANSPOSE)

        region = _state(SubColumn.TRANSPOSE, row=4).region_at(cell)

        assert (region.first_row, region.last_row) == (4, 4)
        assert region.slots == (TrackerSlot(ChannelName.PULSE1, SubColumn.TRANSPOSE),)

    def test_a_cell_of_a_selection_is_raised_on_the_whole_of_it(self) -> None:
        selected = _state(SubColumn.INSTRUMENT, row=4).extend_row(2, ROW_COUNT)
        cell = TrackerCursor(5, ChannelName.PULSE1, SubColumn.INSTRUMENT)

        assert selected.region_at(cell) == selected.region


class TestSelectShapes:
    """The three shapes the grid states, each running the whole frame and ending at its far corner."""

    def test_selecting_all_reaches_every_row_and_every_slot(self) -> None:
        selected = _state(SubColumn.TRANSPOSE, row=4).select_all(ROW_COUNT)

        region = selected.region
        assert region is not None
        assert (region.first_row, region.last_row) == (0, ROW_COUNT - 1)
        assert (region.first_slot, region.last_slot) == (0, SLOT_COUNT - 1)

    def test_selecting_a_column_reaches_the_cursor_s_channel_and_its_subcolumns(self) -> None:
        cell = TrackerCursor(4, ChannelName.TRIANGLE, SubColumn.TRANSPOSE)

        selected = _state(SubColumn.TRANSPOSE, row=4).select_column(cell, ROW_COUNT)

        region = selected.region
        assert region is not None
        assert (region.first_row, region.last_row) == (0, ROW_COUNT - 1)
        assert region.slots == tuple(TrackerSlot(ChannelName.TRIANGLE, subcolumn) for subcolumn in SubColumn)

    def test_the_sample_column_is_a_column_like_any_other(self) -> None:
        cell = TrackerCursor(4, None, SubColumn.VOLUME)

        selected = _state(SubColumn.VOLUME, row=4, channel=None).select_column(cell, ROW_COUNT)

        region = selected.region
        assert region is not None
        assert region.columns == (None,)

    def test_selecting_a_subcolumn_reaches_the_one_slot_the_cursor_stands_on(self) -> None:
        cell = TrackerCursor(4, ChannelName.NOISE, SubColumn.VOLUME)

        selected = _state(SubColumn.VOLUME, row=4, channel=ChannelName.NOISE).select_subcolumn(cell, ROW_COUNT)

        region = selected.region
        assert region is not None
        assert (region.first_row, region.last_row) == (0, ROW_COUNT - 1)
        assert region.slots == (TrackerSlot(ChannelName.NOISE, SubColumn.VOLUME),)

    def test_a_shape_stands_the_cursor_on_the_last_row_it_reaches(self) -> None:
        """A shape ends where the next Shift+arrow starts, which is the far corner it covers."""
        cell = TrackerCursor(4, ChannelName.PULSE1, SubColumn.INSTRUMENT)

        selected = _state(SubColumn.INSTRUMENT, row=4).select_column(cell, ROW_COUNT)

        assert selected.cursor == TrackerCursor(ROW_COUNT - 1, ChannelName.PULSE1, SubColumn.VOLUME)
        assert selected.anchor == TrackerCursor(0, ChannelName.PULSE1, SubColumn.INSTRUMENT)

    def test_a_frame_holding_no_rows_selects_nothing(self) -> None:
        state = _state(SubColumn.INSTRUMENT)

        assert state.select_all(0) is state


class TestColumnNavigation:
    def test_tab_preserves_subcolumn(self) -> None:
        state = _state(SubColumn.VOLUME, channel=ChannelName.PULSE1)
        moved = state.navigate_column_by(1)
        assert moved.cursor is not None
        assert moved.cursor.channel != ChannelName.PULSE1
        assert moved.cursor.subcolumn is SubColumn.VOLUME

    def test_shift_tab_preserves_subcolumn(self) -> None:
        state = _state(SubColumn.TRANSPOSE, channel=ChannelName.PULSE1)
        moved = state.navigate_column_by(-1)
        assert moved.cursor is not None
        assert moved.cursor.subcolumn is SubColumn.TRANSPOSE

    def test_tab_preserves_row(self) -> None:
        state = _state(SubColumn.VOLUME, row=5, channel=ChannelName.PULSE1)
        moved = state.navigate_column_by(1)
        assert moved.cursor is not None
        assert moved.cursor.row == 5
