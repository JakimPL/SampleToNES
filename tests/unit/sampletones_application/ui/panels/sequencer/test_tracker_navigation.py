from dataclasses import dataclass
from types import SimpleNamespace
from typing import List, Tuple

import pytest

from sampletones_application.ui.panels.sequencer.input.tracker import TrackerCursor, TrackerInputState
from sampletones_application.ui.panels.sequencer.tracker import panel as tracker
from sampletones_application.ui.panels.sequencer.tracker.band import UNMEASURED_BAND, TrackerBand, TrackerRows
from sampletones_application.ui.panels.sequencer.tracker.context import ContextRows
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_application.ui.panels.sequencer.tracker.themes import TrackerThemes
from sampletones_application.utils.gui.keyboard import KeyEvent
from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.keys import KEY_PAGE_DOWN, KEY_PAGE_UP
from sampletones_application.utils.gui.keyboard.modifiers import NO_MODIFIERS
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_application.view_model.sequencer.tracker import NO_REACH
from sampletones_core.project.song_position import SongPosition
from sampletones_shared.types.callback import VoidCallback
from tests.suite.shortcuts import shipped_source

PAGE_SIZE = 16
CURSOR_ROW = 5
ROW_COUNT = 65
ROW_HEIGHT = 20.0
BAND_ROWS = 9.5
PLAYING_ROW = 12

SHOWN_FRAME = 3
OTHER_FRAME = 4


def _panel() -> GUISequencerTrackerPanel:
    panel = GUISequencerTrackerPanel.__new__(GUISequencerTrackerPanel)
    panel._shortcuts = shipped_source()
    panel._input_state = TrackerInputState(
        cursor=TrackerCursor(CURSOR_ROW, None, SubColumn.VOICE),
        pending="",
    )
    panel._layout = SimpleNamespace(tracker=SimpleNamespace(page_size=PAGE_SIZE, row_height=ROW_HEIGHT))
    panel._band = TrackerBand(height=BAND_ROWS * ROW_HEIGHT, row_height=ROW_HEIGHT)
    panel._displayed_frame = SHOWN_FRAME
    panel._playing_frame = None
    panel._playing_row = None
    panel._painted_row = None
    panel._follows_playing_row = False
    panel._rows_layout = TrackerRows(reach=panel._band.reach, frame_rows=ROW_COUNT)
    panel._context = ContextRows(layout=panel._layout, themes=TrackerThemes(panel._layout), subcolumn_widths={})
    panel._settings = SimpleNamespace(first_highlight=4, second_highlight=16)
    panel._rows = {row_index: f"row_{row_index}" for row_index in range(ROW_COUNT)}
    return panel


def _playhead(frame_index: int, row_index: int) -> SongPosition:
    """The playhead standing on a row of an order frame."""
    return SongPosition(order_position=frame_index, row_index=row_index)


def _press(text: str) -> KeyEvent:
    """The press a written combination names, as the router delivers it."""
    combination = KeyCombination.parse(text)
    return KeyEvent(key=combination.key, modifiers=combination.modifiers)


def _record_scrolls(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """The scrolls the grid is asked for, in the order it is asked for them."""
    scrolls: List[float] = []
    monkeypatch.setattr(tracker.dpg, "does_item_exist", lambda tag: True)
    monkeypatch.setattr(tracker.dpg, "set_y_scroll", lambda tag, value: scrolls.append(value))
    return scrolls


def _take_states(monkeypatch: pytest.MonkeyPatch, panel: GUISequencerTrackerPanel) -> None:
    """Has the panel take each input state a key leads to, leaving out the highlights it paints."""

    def take(state: TrackerInputState) -> None:
        panel._input_state = state

    monkeypatch.setattr(panel, "_apply_state", take)


def _middle_off_center(panel: GUISequencerTrackerPanel, row_index: int, scroll: float) -> float:
    """How far a row's middle stands from the band's middle once the grid is scrolled to ``scroll``."""
    top = panel._rows_layout.body_row(row_index) * ROW_HEIGHT - scroll
    return top + ROW_HEIGHT / 2 - panel._band.height / 2


def _scroll_max(panel: GUISequencerTrackerPanel) -> float:
    """How far the grid scrolls: every row below the header, less the band showing them."""
    return panel._rows_layout.body_rows * ROW_HEIGHT - panel._band.height


@dataclass(frozen=True)
class KeyLanding:
    """A key, and the row it carries the cursor to from :data:`CURSOR_ROW`."""

    press: str
    row_index: int


KEY_LANDINGS = [
    KeyLanding(press="Down", row_index=CURSOR_ROW + 1),
    KeyLanding(press="Up", row_index=CURSOR_ROW - 1),
    KeyLanding(press="PageDown", row_index=CURSOR_ROW + PAGE_SIZE),
    KeyLanding(press="PageUp", row_index=0),
    KeyLanding(press="Home", row_index=0),
    KeyLanding(press="End", row_index=ROW_COUNT - 1),
    KeyLanding(press="Shift+End", row_index=ROW_COUNT - 1),
]


class TestTheCursorStandsAtTheCenter:
    """A key carrying the cursor to another row brings that row to the band's center."""

    @pytest.mark.parametrize("landing", KEY_LANDINGS, ids=lambda landing: landing.press)
    def test_the_row_a_key_lands_on_is_centered(
        self,
        landing: KeyLanding,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        panel = _panel()
        _take_states(monkeypatch, panel)
        scrolls = _record_scrolls(monkeypatch)

        assert panel._on_key_pressed(_press(landing.press)) is True

        cursor = panel._input_state.cursor
        assert cursor is not None
        assert cursor.row == landing.row_index
        assert len(scrolls) == 1
        assert _middle_off_center(panel, landing.row_index, scrolls[0]) == pytest.approx(0.0)
        assert 0.0 <= scrolls[0] <= _scroll_max(panel)

    def test_a_key_keeping_the_row_scrolls_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        _take_states(monkeypatch, panel)
        scrolls = _record_scrolls(monkeypatch)

        panel._on_key_pressed(_press("Right"))

        assert scrolls == []

    def test_a_band_awaiting_its_measurement_scrolls_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        panel._band = TrackerBand(height=UNMEASURED_BAND, row_height=ROW_HEIGHT)
        _take_states(monkeypatch, panel)
        scrolls = _record_scrolls(monkeypatch)

        panel._on_key_pressed(_press("Down"))

        assert scrolls == []

    def test_a_followed_playhead_keeps_the_band_on_the_sounding_row(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """While the grid follows playback, the song holds the center and a key only moves the cursor."""
        panel = _panel()
        panel.set_row_following(True)
        panel._playing_frame = SHOWN_FRAME
        panel._playing_row = PLAYING_ROW
        _take_states(monkeypatch, panel)
        scrolls = _record_scrolls(monkeypatch)

        panel._on_key_pressed(_press("Down"))

        assert len(scrolls) == 1
        assert _middle_off_center(panel, PLAYING_ROW, scrolls[0]) == pytest.approx(0.0)


class TestPlayheadFollowing:
    """The grid keeps the sounding row at the band's center for as long as it follows the playhead."""

    @pytest.mark.parametrize("row_index", [0, PLAYING_ROW, ROW_COUNT - 1])
    def test_a_followed_row_is_centered(self, row_index: int, monkeypatch: pytest.MonkeyPatch) -> None:
        """The first and the last row reach the center too, the rows of the song either side holding the room."""
        panel = _panel()
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        scrolls = _record_scrolls(monkeypatch)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(SHOWN_FRAME, row_index))

        assert len(scrolls) == 1
        assert _middle_off_center(panel, row_index, scrolls[0]) == pytest.approx(0.0)
        assert 0.0 <= scrolls[0] <= _scroll_max(panel)

    def test_an_unfollowed_row_stays_where_the_reader_left_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        scrolls = _record_scrolls(monkeypatch)

        panel.set_row_following(False)
        panel.set_playing_position(_playhead(SHOWN_FRAME, PLAYING_ROW))

        assert scrolls == []

    def test_a_row_of_another_frame_holds_the_grid_where_it_is(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A row belongs to its own pattern, so the grid travels to it once that frame is shown."""
        panel = _panel()
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        scrolls = _record_scrolls(monkeypatch)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(OTHER_FRAME, PLAYING_ROW))

        assert scrolls == []

    def test_a_cleared_playhead_leaves_the_scroll_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Stopping drops the mark, and the grid keeps the position it was scrolled to."""
        panel = _panel()
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        scrolls = _record_scrolls(monkeypatch)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(SHOWN_FRAME, PLAYING_ROW))
        panel.set_playing_position(None)

        assert len(scrolls) == 1

    def test_a_grid_awaiting_its_band_is_left_alone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A band is measured once the grid has laid out, and nothing is centered before."""
        panel = _panel()
        panel._band = TrackerBand(height=UNMEASURED_BAND, row_height=ROW_HEIGHT)
        monkeypatch.setattr(panel, "_paint_row", lambda row_index: None)
        scrolls = _record_scrolls(monkeypatch)

        panel.set_row_following(True)
        panel.set_playing_position(_playhead(SHOWN_FRAME, PLAYING_ROW))

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

    @pytest.mark.parametrize("written", ["Ctrl+D", "Alt+D", "Super+D"])
    def test_a_modified_key_reaches_the_application(
        self,
        monkeypatch: pytest.MonkeyPatch,
        written: str,
    ) -> None:
        """Ctrl+D opens the display settings, so cell entry keeps the plain hex key alone."""
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press(written)) is False
        assert states == []

    def test_a_key_under_shift_types_as_a_capital(self, monkeypatch: pytest.MonkeyPatch) -> None:
        panel = _panel()
        states: List[TrackerInputState] = []
        monkeypatch.setattr(panel, "_apply_state", states.append)

        assert panel._on_key_pressed(_press("Shift+C")) is True
        assert states[-1].pending == "C"
