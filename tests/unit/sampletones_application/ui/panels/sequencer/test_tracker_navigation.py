from dataclasses import dataclass
from types import SimpleNamespace
from typing import List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer import tracker
from sampletones_application.ui.panels.sequencer.input.cursor import TrackerCursor
from sampletones_application.ui.panels.sequencer.input.state import TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import GUISequencerTrackerPanel
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN, KEY_PAGE_UP
from sampletones_application.utils.gui.keyboard.modifiers import NO_MODIFIERS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.types.callback import VoidCallback
from tests.suite.shortcuts import shipped_source

PAGE_SIZE = 16
CURSOR_ROW = 5
ROW_COUNT = 65
SCROLL_MAX = 640.0
ROW_PITCH = 20.0
BAND_TOP = 100.0
LAST_HEADING_ROW = 32

SHOWN_FRAME = 3
OTHER_FRAME = 4


def _panel() -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(
        cursor=TrackerCursor(CURSOR_ROW, None, SubColumn.INSTRUMENT),
        pending="",
    )
    panel._layout = SimpleNamespace(tracker=SimpleNamespace(page_size=PAGE_SIZE))
    panel._displayed_frame = SHOWN_FRAME
    panel._playing_frame = None
    panel._playing_row = None
    panel._painted_row = None
    panel._follows_playing_row = False
    panel._current_row_count = ROW_COUNT
    panel._rows = {row_index: f"row_{row_index}" for row_index in range(ROW_COUNT)}
    return panel


def _playhead(frame_index: int, row_index: int) -> SongPosition:
    """The playhead standing on a row of an order frame."""
    return SongPosition(order_position=frame_index, row_index=row_index)


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


class TestGridPageNavigation:
    """PageUp and PageDown jump the cursor a page of rows, matching the key codes DearPyGui delivers,
    and reveal the row they land on."""

    def test_page_up_moves_up_one_page_and_scrolls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        scrolls: List[None] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)
        monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: scrolls.append(None))

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_UP, modifiers=NO_MODIFIERS)) is True
        assert moves == [-PAGE_SIZE]
        assert scrolls == [None]

    def test_page_down_moves_down_one_page_and_scrolls(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        scrolls: List[None] = []
        monkeypatch.setattr(panel, "_move_row", moves.append)
        monkeypatch.setattr(panel, "_scroll_cursor_into_view", lambda: scrolls.append(None))

        assert panel._on_key_pressed(KeyEvent(key=KEY_PAGE_DOWN, modifiers=NO_MODIFIERS)) is True
        assert moves == [PAGE_SIZE]
        assert scrolls == [None]


@dataclass(frozen=True)
class RowPlacementCase:
    """A row of the frame, and the scroll that places it."""

    row_index: int
    scroll: float


ROW_PLACEMENTS = [
    RowPlacementCase(row_index=0, scroll=0.0),
    RowPlacementCase(row_index=(ROW_COUNT - 1) // 2, scroll=SCROLL_MAX / 2),
    RowPlacementCase(row_index=ROW_COUNT - 1, scroll=SCROLL_MAX),
]

BAND_TOP_PLACEMENTS = [
    RowPlacementCase(row_index=0, scroll=0.0),
    RowPlacementCase(row_index=10, scroll=10 * ROW_PITCH),
    RowPlacementCase(row_index=LAST_HEADING_ROW, scroll=SCROLL_MAX),
    RowPlacementCase(row_index=LAST_HEADING_ROW + 8, scroll=SCROLL_MAX),
    RowPlacementCase(row_index=ROW_COUNT - 1, scroll=SCROLL_MAX),
]


def _row_top(tag: str) -> List[float]:
    """Where a laid-out row stands, the rows stacked one pitch apart below the band's top."""
    return [0.0, BAND_TOP + int(tag.removeprefix("row_")) * ROW_PITCH]


def _record_scrolls(monkeypatch: pytest.MonkeyPatch, scroll_max: float) -> List[float]:
    """The scrolls a placement asks of a laid-out grid, in the order it asks for them."""
    scrolls: List[float] = []
    monkeypatch.setattr(tracker.dpg, "does_item_exist", lambda tag: True)
    monkeypatch.setattr(tracker.dpg, "get_y_scroll_max", lambda tag: scroll_max)
    monkeypatch.setattr(tracker.dpg, "get_item_rect_min", _row_top)
    monkeypatch.setattr(tracker.dpg, "set_y_scroll", lambda tag, value: scrolls.append(value))
    return scrolls


class TestPlayheadFollowing:
    """The grid carries the sounding row to the head of the band for as long as it follows the
    playhead."""

    def test_a_followed_row_is_revealed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        revealed: List[int] = []
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        monkeypatch.setattr(panel, "_scroll_row_to_band_top", revealed.append)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))

        assert revealed == [12]

    def test_an_unfollowed_row_stays_where_the_reader_left_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        revealed: List[int] = []
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        monkeypatch.setattr(panel, "_scroll_row_to_band_top", revealed.append)

        panel.set_row_following(False)
        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))

        assert revealed == []

    def test_a_row_of_another_frame_holds_the_grid_where_it_is(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A row belongs to its own pattern, so the grid travels to it once that frame is shown."""
        panel = _panel()
        revealed: List[int] = []
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        monkeypatch.setattr(panel, "_scroll_row_to_band_top", revealed.append)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(OTHER_FRAME, 12))

        assert revealed == []

    def test_a_cleared_playhead_leaves_the_scroll_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stopping drops the mark, and the grid keeps the position it was scrolled to."""
        panel = _panel()
        revealed: List[int] = []
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        monkeypatch.setattr(panel, "_scroll_row_to_band_top", revealed.append)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))
        panel.set_playing_position(None)

        assert revealed == [12]

    @pytest.mark.parametrize("case", BAND_TOP_PLACEMENTS, ids=lambda case: f"row_{case.row_index}")
    def test_a_row_is_carried_to_the_head_of_the_band(
        self,
        case: RowPlacementCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each row heads the band by the height of the rows above it, as far as the grid scrolls."""
        panel = _panel()
        scrolls = _record_scrolls(monkeypatch, SCROLL_MAX)

        panel._scroll_row_to_band_top(case.row_index)

        assert scrolls == [pytest.approx(case.scroll)]

    def test_a_frame_that_fits_the_band_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A frame shorter than the band shows every row already, so the grid holds still."""
        panel = _panel()
        scrolls = _record_scrolls(monkeypatch, 0.0)

        panel._scroll_row_to_band_top(4)

        assert scrolls == []

    def test_a_grid_awaiting_its_layout_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rows reach the grid a frame before they are placed, and measure nothing until they are."""
        panel = _panel()
        panel._rows = {}
        scrolls = _record_scrolls(monkeypatch, SCROLL_MAX)

        panel._scroll_row_to_band_top(4)

        assert scrolls == []


class TestPlayheadPainting:
    """The mark is drawn on the frame the grid's scroll lands on, so the two arrive as one."""

    def test_the_mark_waits_for_the_frame_its_scroll_lands_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        painted, paint = _deferred_painting(monkeypatch, panel)

        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))

        assert panel._painted_row is None
        assert painted == []

        paint()

        assert panel._painted_row == 12
        assert painted == [12]

    def test_the_row_the_playhead_left_is_cleared(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        painted, paint = _deferred_painting(monkeypatch, panel)

        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))
        paint()
        panel.set_playing_position(_playhead(SHOWN_FRAME, 13))
        paint()

        assert painted == [12, 12, 13]

    def test_a_stopped_playhead_clears_the_row_it_stood_on(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        painted, paint = _deferred_painting(monkeypatch, panel)

        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))
        paint()
        panel.set_playing_position(None)
        paint()

        assert panel._painted_row is None
        assert painted == [12, 12]

    def test_the_mark_arrives_with_the_frame_the_playhead_moved_to(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A followed playhead crossing a frame boundary shows the next frame, then marks its row."""
        panel = _panel()
        painted, paint = _deferred_painting(monkeypatch, panel)

        panel.set_playing_position(_playhead(SHOWN_FRAME, 12))
        paint()
        panel._show_frame(OTHER_FRAME)
        panel.set_playing_position(_playhead(OTHER_FRAME, 0))
        paint()

        assert panel._painted_row == 0
        assert painted == [12, 12, 0]


def _deferred_painting(
    monkeypatch: pytest.MonkeyPatch,
    panel: GUISequencerTrackerPanel,
) -> Tuple[List[int], VoidCallback]:
    """The rows a panel paints, and the call that runs the frame's painting on demand."""
    painted: List[int] = []
    held: List[VoidCallback] = []

    def hold(callback: VoidCallback, frame_count: int = 1) -> None:
        assert frame_count == tracker.PLAYHEAD_PAINT_FRAMES
        held.append(callback)

    monkeypatch.setattr(tracker.FrameCallbackManager, "set_frame_callback", hold)
    monkeypatch.setattr(panel, "_paint_row", painted.append)

    def paint() -> None:
        held.pop()()

    return painted, paint


class TestCursorPlacement:
    """A cursor jump places the row across the band, from its top on the first row to its bottom on
    the last."""

    @pytest.mark.parametrize("case", ROW_PLACEMENTS, ids=lambda case: f"row_{case.row_index}")
    def test_a_row_is_placed_across_the_band(
        self,
        case: RowPlacementCase,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel()
        scrolls = _record_scrolls(monkeypatch, SCROLL_MAX)

        panel._scroll_row_into_view(case.row_index)

        assert scrolls == [pytest.approx(case.scroll)]

    def test_the_cursor_is_placed_by_that_rule(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        revealed: List[int] = []
        monkeypatch.setattr(panel, "_scroll_row_into_view", revealed.append)

        panel._scroll_cursor_into_view()

        assert revealed == [CURSOR_ROW]


class TestGridColumnNavigation:
    """Tab steps to the next channel column and Shift+Tab back, each its own action in the scheme."""

    def test_the_next_column_key_steps_forward(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_column", moves.append)

        assert panel._on_key_pressed(_press("Tab")) is True
        assert moves == [1]

    def test_the_previous_column_key_steps_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        moves: List[int] = []
        monkeypatch.setattr(panel, "_move_column", moves.append)

        assert panel._on_key_pressed(_press("Shift+Tab")) is True
        assert moves == [-1]


class TestGridCellEntry:
    def test_a_note_key_types_into_the_cell_under_the_cursor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press("C")) is True
        assert states[-1].pending == "C"

    def test_a_modified_key_reaches_the_application(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ctrl+C carries no tracker action, so cell entry keeps the plain key alone."""
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press("Ctrl+C")) is False
        assert states == []
