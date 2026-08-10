from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import tracker as tracker_module
from sampletones_application.ui.panels.sequencer.columns import (
    HEADER_TABLE_ROW,
    tracker_table_column,
    tracker_table_row,
)
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.sequencer.settings import (
    SequencerSettingsViewModel,
)
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.types.application import ColorRGBA

PATTERN_ROWS = 4
HEADER_AND_PATTERN_ROWS = PATTERN_ROWS + 1

SHOWN_FRAME = 3
OTHER_FRAME = 4

ROWS_PER_BEAT = 2
ROWS_PER_BAR = 4
BAR_ROWS = (0,)
BEAT_ROWS = (2,)
PLAIN_ROWS = (1, 3)

CURSOR_ROW: ColorRGBA = (255, 255, 255, 24)
CELL_CURSOR: ColorRGBA = (102, 187, 255, 160)
PATTERN_HIGHLIGHT: ColorRGBA = (255, 255, 255, 64)
PLAYBACK_ROW: ColorRGBA = (100, 220, 100, 64)
BEAT_ROW: ColorRGBA = (255, 255, 255, 14)
BAR_ROW: ColorRGBA = (255, 255, 255, 30)
HEADER_SHADE: ColorRGBA = (70, 65, 92, 255)


class _TableRecorder:
    """Captures the row and cell highlight calls, standing in for a live tracker table."""

    def __init__(self, *, row_children: Sequence[int]) -> None:
        self.row_children = list(row_children)
        self.highlighted_rows: Dict[int, ColorRGBA] = {}
        self.unhighlighted_rows: List[int] = []
        self.highlighted_cells: Dict[Tuple[int, int], ColorRGBA] = {}
        self.unhighlighted_cells: List[Tuple[int, int]] = []

    def does_item_exist(self, item: str) -> bool:
        return True

    def get_item_children(self, item: str, slot: int) -> List[int]:
        return self.row_children

    def highlight_table_row(self, table: str, row: int, color: ColorRGBA) -> None:
        self.highlighted_rows[row] = color
        if row in self.unhighlighted_rows:
            self.unhighlighted_rows.remove(row)

    def unhighlight_table_row(self, table: str, row: int) -> None:
        self.unhighlighted_rows.append(row)
        self.highlighted_rows.pop(row, None)

    def highlight_table_cell(self, table: str, row: int, column: int, color: ColorRGBA) -> None:
        self.highlighted_cells[(row, column)] = color

    def unhighlight_table_cell(self, table: str, row: int, column: int) -> None:
        self.unhighlighted_cells.append((row, column))


def _settings(
    *,
    first_highlight: int = ROWS_PER_BEAT,
    second_highlight: int = ROWS_PER_BAR,
) -> SequencerSettingsViewModel:
    """The module settings the panel reads its metre out of."""
    return SequencerSettingsViewModel(
        nes_frequency=60,
        tempo=150,
        speed=6,
        rows_per_pattern=PATTERN_ROWS,
        first_highlight=first_highlight,
        second_highlight=second_highlight,
    )


def _panel() -> GUISequencerTrackerPanel:
    """Builds a panel around the state the row backgrounds read, with no DearPyGui context."""
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._settings = _settings()
    panel._layout = SimpleNamespace(
        colors=SimpleNamespace(
            cursor_row=LiteralColor(CURSOR_ROW),
            cell_cursor=LiteralColor(CELL_CURSOR),
            pattern_highlight=LiteralColor(PATTERN_HIGHLIGHT),
            playback_row=LiteralColor(PLAYBACK_ROW),
            rows=SimpleNamespace(
                beat=LiteralColor(BEAT_ROW),
                bar=LiteralColor(BAR_ROW),
            ),
        ),
    )
    panel._current_row_count = PATTERN_ROWS
    panel._highlighted_row = None
    panel._displayed_frame = SHOWN_FRAME
    panel._playing_frame = None
    panel._playing_row = None
    panel._painted_row = None
    panel._follows_playing_row = False
    panel._input_state = TrackerInputState()
    return panel


def _playhead(frame_index: int, row_index: int) -> SongPosition:
    """The playhead standing on a row of an order frame."""
    return SongPosition(order_position=frame_index, row_index=row_index)


def _place_cursor(
    panel: GUISequencerTrackerPanel,
    row_index: int,
    generator: Optional[GeneratorName],
) -> None:
    """Puts the cursor where the panel's own state keeps it, the way an edit action does."""
    panel._input_state = TrackerInputState(
        cursor=TrackerCursor(row_index, generator, SubColumn.INSTRUMENT),
        pending="",
    )


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _TableRecorder:
    instance = _TableRecorder(row_children=range(HEADER_AND_PATTERN_ROWS))
    monkeypatch.setattr(tracker_module.dpg, "does_item_exist", instance.does_item_exist)
    monkeypatch.setattr(tracker_module.dpg, "get_item_children", instance.get_item_children)
    monkeypatch.setattr(tracker_module.dpg, "highlight_table_row", instance.highlight_table_row)
    monkeypatch.setattr(tracker_module.dpg, "unhighlight_table_row", instance.unhighlight_table_row)
    monkeypatch.setattr(tracker_module.dpg, "highlight_table_cell", instance.highlight_table_cell)
    monkeypatch.setattr(tracker_module.dpg, "unhighlight_table_cell", instance.unhighlight_table_cell)
    return instance


class TestLiveRowCount:
    def test_the_count_covers_the_pattern_rows_alone(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        assert panel._live_row_count() == PATTERN_ROWS

    def test_a_table_holding_only_the_header_reports_no_pattern_rows(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        recorder.row_children = [0]

        assert panel._live_row_count() == 0

    def test_an_unbuilt_table_reports_no_pattern_rows(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        recorder.row_children = []

        assert panel._live_row_count() == 0


class TestRowGrouping:
    def test_the_rows_opening_a_bar_and_a_beat_take_their_shades(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._apply_row_backgrounds()

        assert recorder.highlighted_rows == {
            tracker_table_row(0): BAR_ROW,
            tracker_table_row(2): BEAT_ROW,
        }

    def test_the_rows_between_them_are_left_to_the_stripe(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._apply_row_backgrounds()

        assert recorder.unhighlighted_rows == [tracker_table_row(row) for row in PLAIN_ROWS]

    def test_the_header_row_takes_no_row_background(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._apply_row_backgrounds()

        assert HEADER_TABLE_ROW not in recorder.highlighted_rows
        assert HEADER_TABLE_ROW not in recorder.unhighlighted_rows

    def test_an_edited_metre_retints_the_rows_at_once(self, recorder: _TableRecorder) -> None:
        """The highlights are the project's, so a change to them reaches the grid as a repaint."""
        panel = _panel()
        panel._apply_row_backgrounds()

        panel.update_settings(_settings(first_highlight=1, second_highlight=PATTERN_ROWS))

        assert recorder.highlighted_rows == {
            tracker_table_row(0): BAR_ROW,
            tracker_table_row(1): BEAT_ROW,
            tracker_table_row(2): BEAT_ROW,
            tracker_table_row(3): BEAT_ROW,
        }

    def test_a_row_past_the_live_table_never_reaches_dearpygui(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._paint_row(PATTERN_ROWS)

        assert not recorder.highlighted_rows
        assert not recorder.unhighlighted_rows


class TestCursorHighlight:
    @pytest.mark.parametrize("row_index", PLAIN_ROWS)
    def test_the_cursor_lands_on_the_mapped_table_row(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()
        _place_cursor(panel, row_index, GeneratorName.TRIANGLE)

        panel._apply_cell_highlight(row_index, GeneratorName.TRIANGLE)

        assert recorder.highlighted_rows == {tracker_table_row(row_index): CURSOR_ROW}

    @pytest.mark.parametrize("row_index", BAR_ROWS + BEAT_ROWS)
    def test_the_cursor_on_a_group_row_carries_both_shades(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()
        _place_cursor(panel, row_index, GeneratorName.TRIANGLE)

        panel._apply_cell_highlight(row_index, GeneratorName.TRIANGLE)

        painted = recorder.highlighted_rows[tracker_table_row(row_index)]
        assert painted[3] > CURSOR_ROW[3]

    def test_the_cursor_cell_lands_on_the_mapped_row_and_column(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        _place_cursor(panel, 2, GeneratorName.NOISE)

        panel._apply_cell_highlight(2, GeneratorName.NOISE)

        key = (tracker_table_row(2), tracker_table_column(GeneratorName.NOISE))
        assert recorder.highlighted_cells == {key: CELL_CURSOR}

    def test_no_cursor_ever_paints_the_header_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        for row_index in range(PATTERN_ROWS):
            _place_cursor(panel, row_index, None)
            panel._apply_cell_highlight(row_index, None)

        assert HEADER_TABLE_ROW not in recorder.highlighted_rows

    def test_removing_the_cursor_clears_the_cell_and_the_plain_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._remove_cell_highlight(1, None)

        assert recorder.unhighlighted_rows == [tracker_table_row(1)]
        assert recorder.unhighlighted_cells == [(tracker_table_row(1), tracker_table_column(None))]

    def test_a_group_row_keeps_its_shade_once_the_cursor_leaves(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._remove_cell_highlight(0, None)

        assert recorder.highlighted_rows == {tracker_table_row(0): BAR_ROW}


class TestHoverHighlight:
    def test_hover_lands_on_the_mapped_table_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(3)

        assert recorder.highlighted_rows == {tracker_table_row(3): PATTERN_HIGHLIGHT}

    def test_hover_on_a_group_row_carries_both_shades(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(0)

        painted = recorder.highlighted_rows[tracker_table_row(0)]
        assert painted[3] > PATTERN_HIGHLIGHT[3]

    def test_moving_the_hover_returns_the_row_it_left(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(1)
        panel.highlight_row(3)

        assert recorder.unhighlighted_rows == [tracker_table_row(1)]
        assert recorder.highlighted_rows == {tracker_table_row(3): PATTERN_HIGHLIGHT}

    def test_moving_the_hover_off_a_group_row_gives_it_its_shade_back(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(0)
        panel.highlight_row(3)

        assert recorder.highlighted_rows[tracker_table_row(0)] == BAR_ROW

    def test_dropping_the_hover_clears_the_mapped_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.highlight_row(3)

        panel.highlight_row(None)

        assert recorder.unhighlighted_rows == [tracker_table_row(3)]


class TestPlayingRowHighlight:
    @pytest.mark.parametrize("row_index", PLAIN_ROWS)
    def test_the_playhead_lands_on_the_mapped_table_row(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, row_index))

        assert recorder.highlighted_rows == {tracker_table_row(row_index): PLAYBACK_ROW}

    @pytest.mark.parametrize("row_index", BAR_ROWS + BEAT_ROWS)
    def test_the_playhead_over_a_group_row_carries_both_shades(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, row_index))

        painted = recorder.highlighted_rows[tracker_table_row(row_index)]
        assert painted[3] > PLAYBACK_ROW[3]

    def test_the_playhead_outranks_the_cursor_on_the_same_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        _place_cursor(panel, 1, GeneratorName.PULSE1)

        panel.set_playing_position(_playhead(SHOWN_FRAME, 1))

        assert recorder.highlighted_rows == {tracker_table_row(1): PLAYBACK_ROW}

    def test_the_last_pattern_row_is_still_within_the_table(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, PATTERN_ROWS - 1))

        assert recorder.highlighted_rows

    def test_a_row_beyond_the_pattern_is_left_to_the_next_rebuild(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, PATTERN_ROWS))

        assert not recorder.highlighted_rows

    def test_advancing_the_playhead_returns_the_row_it_left(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, 1))
        panel.set_playing_position(_playhead(SHOWN_FRAME, 3))

        assert recorder.unhighlighted_rows == [tracker_table_row(1)]

    def test_advancing_past_a_group_row_gives_it_its_shade_back(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(SHOWN_FRAME, 0))
        panel.set_playing_position(_playhead(SHOWN_FRAME, 1))

        assert recorder.highlighted_rows[tracker_table_row(0)] == BAR_ROW

    def test_stopping_clears_the_mapped_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.set_playing_position(_playhead(SHOWN_FRAME, 3))

        panel.set_playing_position(None)

        assert recorder.unhighlighted_rows == [tracker_table_row(3)]


class TestPlayheadFrame:
    """The mark reads as the sounding row of the pattern on screen, so it stands on the grid while
    the frame it shows is the frame the playhead sounds."""

    def test_a_row_of_another_frame_leaves_the_grid_alone(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_position(_playhead(OTHER_FRAME, 1))

        assert not recorder.highlighted_rows

    def test_showing_another_frame_returns_the_marked_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.set_playing_position(_playhead(SHOWN_FRAME, 3))

        panel._show_frame(OTHER_FRAME)

        assert recorder.unhighlighted_rows == [tracker_table_row(3)]

    def test_returning_to_the_sounding_frame_marks_its_row_again(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.set_playing_position(_playhead(SHOWN_FRAME, 3))
        panel._show_frame(OTHER_FRAME)

        panel._show_frame(SHOWN_FRAME)

        assert recorder.highlighted_rows == {tracker_table_row(3): PLAYBACK_ROW}

    def test_the_cursor_keeps_its_row_on_a_frame_the_playhead_left(self, recorder: _TableRecorder) -> None:
        """A frame the playhead is away from shows the reader's own cursor on the row it sits on."""
        panel = _panel()
        _place_cursor(panel, 3, GeneratorName.PULSE1)
        panel.set_playing_position(_playhead(SHOWN_FRAME, 3))

        panel._show_frame(OTHER_FRAME)

        assert recorder.highlighted_rows[tracker_table_row(3)] == CURSOR_ROW


class TestHeaderRowBackground:
    def test_every_table_column_of_the_header_takes_the_header_shade(
        self,
        recorder: _TableRecorder,
    ) -> None:
        panel = _panel()
        panel._layout = SimpleNamespace(
            colors=SimpleNamespace(header=SimpleNamespace(background=LiteralColor(HEADER_SHADE)))
        )

        panel._highlight_header_row()

        painted = {row for row, _ in recorder.highlighted_cells}
        columns = {column for _, column in recorder.highlighted_cells}
        assert painted == {HEADER_TABLE_ROW}
        assert columns == set(range(tracker_module.TRACKER_TABLE_COLUMNS))

    def test_the_header_shade_covers_the_sample_and_channel_columns(
        self,
        recorder: _TableRecorder,
    ) -> None:
        """The washes are column highlights, which DearPyGui draws over a row highlight, so the
        header is painted per cell to read as one band."""
        panel = _panel()
        panel._layout = SimpleNamespace(
            colors=SimpleNamespace(header=SimpleNamespace(background=LiteralColor(HEADER_SHADE)))
        )

        panel._highlight_header_row()

        washed: List[Optional[GeneratorName]] = [None, *GeneratorName.items()]
        for generator in washed:
            key = (HEADER_TABLE_ROW, tracker_table_column(generator))
            assert recorder.highlighted_cells[key] == HEADER_SHADE
