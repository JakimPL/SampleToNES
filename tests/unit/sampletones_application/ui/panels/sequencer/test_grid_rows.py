from types import SimpleNamespace
from typing import Dict, List, Optional, Sequence, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import grid as grid_module
from sampletones_application.ui.panels.sequencer.columns import (
    HEADER_TABLE_ROW,
    tracker_table_column,
    tracker_table_row,
)
from sampletones_application.ui.panels.sequencer.grid import GUISequencerGridPanel
from sampletones_application.utils.palette.color import PaletteColor
from sampletones_core.constants.enums import GeneratorName
from sampletones_shared.types.application import ColorRGBA

PATTERN_ROWS = 4
HEADER_AND_PATTERN_ROWS = PATTERN_ROWS + 1

CURSOR_ROW: ColorRGBA = (255, 255, 255, 24)
CELL_CURSOR: ColorRGBA = (102, 187, 255, 160)
PATTERN_HIGHLIGHT: ColorRGBA = (255, 255, 255, 64)
PLAYBACK_ROW: ColorRGBA = (100, 220, 100, 64)
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

    def unhighlight_table_row(self, table: str, row: int) -> None:
        self.unhighlighted_rows.append(row)

    def highlight_table_cell(self, table: str, row: int, column: int, color: ColorRGBA) -> None:
        self.highlighted_cells[(row, column)] = color

    def unhighlight_table_cell(self, table: str, row: int, column: int) -> None:
        self.unhighlighted_cells.append((row, column))


def _panel() -> GUISequencerGridPanel:
    """Builds a panel around the state the row highlights read, with no DearPyGui context."""
    panel = GUISequencerGridPanel.__new__(GUISequencerGridPanel)
    panel._layout = SimpleNamespace(
        colors=SimpleNamespace(
            cursor_row=PaletteColor(value=CURSOR_ROW),
            cell_cursor=PaletteColor(value=CELL_CURSOR),
            pattern_highlight=PaletteColor(value=PATTERN_HIGHLIGHT),
            playback_row=PaletteColor(value=PLAYBACK_ROW),
        ),
    )
    panel._current_row_count = PATTERN_ROWS
    panel._highlighted_row = None
    panel._playing_row = None
    return panel


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> _TableRecorder:
    instance = _TableRecorder(row_children=range(HEADER_AND_PATTERN_ROWS))
    monkeypatch.setattr(grid_module.dpg, "does_item_exist", instance.does_item_exist)
    monkeypatch.setattr(grid_module.dpg, "get_item_children", instance.get_item_children)
    monkeypatch.setattr(grid_module.dpg, "highlight_table_row", instance.highlight_table_row)
    monkeypatch.setattr(grid_module.dpg, "unhighlight_table_row", instance.unhighlight_table_row)
    monkeypatch.setattr(grid_module.dpg, "highlight_table_cell", instance.highlight_table_cell)
    monkeypatch.setattr(grid_module.dpg, "unhighlight_table_cell", instance.unhighlight_table_cell)
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


class TestCursorHighlight:
    @pytest.mark.parametrize("row_index", range(PATTERN_ROWS))
    def test_the_cursor_lands_on_the_mapped_table_row(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()

        panel._apply_cell_highlight(row_index, GeneratorName.TRIANGLE)

        assert recorder.highlighted_rows == {tracker_table_row(row_index): CURSOR_ROW}

    def test_the_cursor_cell_lands_on_the_mapped_row_and_column(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._apply_cell_highlight(2, GeneratorName.NOISE)

        key = (tracker_table_row(2), tracker_table_column(GeneratorName.NOISE))
        assert recorder.highlighted_cells == {key: CELL_CURSOR}

    def test_no_cursor_ever_paints_the_header_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        for row_index in range(PATTERN_ROWS):
            panel._apply_cell_highlight(row_index, None)

        assert HEADER_TABLE_ROW not in recorder.highlighted_rows

    def test_removing_the_cursor_clears_the_mapped_row_and_cell(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel._remove_cell_highlight(1, None)

        assert recorder.unhighlighted_rows == [tracker_table_row(1)]
        assert recorder.unhighlighted_cells == [(tracker_table_row(1), tracker_table_column(None))]


class TestHoverHighlight:
    def test_hover_lands_on_the_mapped_table_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(3)

        assert recorder.highlighted_rows == {tracker_table_row(3): PATTERN_HIGHLIGHT}

    def test_moving_the_hover_clears_the_row_it_left(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.highlight_row(0)
        panel.highlight_row(2)

        assert recorder.unhighlighted_rows == [tracker_table_row(0)]

    def test_dropping_the_hover_clears_the_mapped_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.highlight_row(2)

        panel.highlight_row(None)

        assert recorder.unhighlighted_rows == [tracker_table_row(2)]


class TestPlayingRowHighlight:
    @pytest.mark.parametrize("row_index", range(PATTERN_ROWS))
    def test_the_playhead_lands_on_the_mapped_table_row(
        self,
        recorder: _TableRecorder,
        row_index: int,
    ) -> None:
        panel = _panel()

        panel.set_playing_row(row_index)

        assert recorder.highlighted_rows == {tracker_table_row(row_index): PLAYBACK_ROW}

    def test_the_last_pattern_row_is_still_within_the_table(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_row(PATTERN_ROWS - 1)

        assert recorder.highlighted_rows

    def test_a_row_beyond_the_pattern_is_left_to_the_next_rebuild(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_row(PATTERN_ROWS)

        assert not recorder.highlighted_rows

    def test_advancing_the_playhead_clears_the_row_it_left(self, recorder: _TableRecorder) -> None:
        panel = _panel()

        panel.set_playing_row(1)
        panel.set_playing_row(2)

        assert recorder.unhighlighted_rows == [tracker_table_row(1)]

    def test_stopping_clears_the_mapped_row(self, recorder: _TableRecorder) -> None:
        panel = _panel()
        panel.set_playing_row(2)

        panel.set_playing_row(None)

        assert recorder.unhighlighted_rows == [tracker_table_row(2)]


class TestHeaderRowBackground:
    def test_every_table_column_of_the_header_takes_the_header_shade(
        self,
        recorder: _TableRecorder,
    ) -> None:
        panel = _panel()
        panel._layout = SimpleNamespace(
            colors=SimpleNamespace(header=SimpleNamespace(background=PaletteColor(value=HEADER_SHADE)))
        )

        panel._highlight_header_row()

        painted = {row for row, _ in recorder.highlighted_cells}
        columns = {column for _, column in recorder.highlighted_cells}
        assert painted == {HEADER_TABLE_ROW}
        assert columns == set(range(grid_module.TRACKER_TABLE_COLUMNS))

    def test_the_header_shade_covers_the_sample_and_channel_columns(
        self,
        recorder: _TableRecorder,
    ) -> None:
        """The washes are column highlights, which DearPyGui draws over a row highlight, so the
        header is painted per cell to read as one band."""
        panel = _panel()
        panel._layout = SimpleNamespace(
            colors=SimpleNamespace(header=SimpleNamespace(background=PaletteColor(value=HEADER_SHADE)))
        )

        panel._highlight_header_row()

        washed: List[Optional[GeneratorName]] = [None, *GeneratorName.items()]
        for generator in washed:
            key = (HEADER_TABLE_ROW, tracker_table_column(generator))
            assert recorder.highlighted_cells[key] == HEADER_SHADE
