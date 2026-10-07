from dataclasses import dataclass
from typing import Final, FrozenSet, List, Optional, Tuple

from sampletones_application.tags.sequencer import TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.tracker.band.constants import (
    BLANK,
    CHANNEL,
    CLICKED_ROW,
    FIRST_ROWS_OF_A_FRAME,
    LAST_ROW,
    LAST_ROWS_OF_A_FRAME,
    NEIGHBORS,
    PLAYING_FRAMES,
    SECOND_FRAME,
    SLOT,
    STEPS_DOWN,
)
from tests.screens.sequencer.tracker.band.steps import (
    expect_centered,
    expect_paused,
    expect_playing,
    expect_stopped,
    press,
    show_frame,
)
from tests.suite.screens.dearpygui.geometry import Rect
from tests.suite.screens.dearpygui.items.reading import read_item
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import on_the_sequencer
from tests.suite.screens.views.tracker import tracker_cell

SETTLING_FRAMES: Final[int] = 8
ALPHA: Final[int] = 3


def cell_box(screen: Screen, row: int) -> Optional[Rect]:
    """Where the clicked channel's slot on ``row`` stands on the screen."""
    return screen.bridge.ask(lambda: read_item(tracker_cell(row, CHANNEL, SLOT)).rect)


def alpha(color: Optional[Tuple[float, ...]]) -> float:
    """How opaque a color is drawn."""
    assert color is not None
    return color[ALPHA]


@dataclass(frozen=True)
class PausedReading:
    """What a paused song left on the band: the row at its middle, and every row drawn with a tint."""

    center: int
    tinted: FrozenSet[int]


def center_on_the_first_row(screen: Screen) -> None:
    """Steps the caret off the first row and back, which a key landing on a row brings to the center."""
    press(screen, ShortcutId.TRACKER_NEXT_ROW, 1)
    press(screen, ShortcutId.TRACKER_PREVIOUS_ROW, 1)
    expect_centered(screen, 0)


class TestTheCursorStandsAtTheCenter:
    """A key carrying the caret to another row brings that row to the middle of the band.

    A click on a row puts the caret there and leaves the grid where it stands. Keys then carry the caret
    down: the row each lands on stands at the middle, the last row of the frame among them.
    """

    def test_keys_carry_the_rows_under_the_middle(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def a_click_leaves_the_grid_where_it_stands(screen: Screen) -> None:
            on_the_sequencer(screen)
            before = cell_box(screen, CLICKED_ROW)

            tracker.click(CLICKED_ROW, CHANNEL, SLOT)
            screen.expect(lambda: tracker.has_caret(CLICKED_ROW, CHANNEL), bool, description="the caret placed")
            screen.frames(SETTLING_FRAMES)

            assert cell_box(screen, CLICKED_ROW) == before

        def a_step_brings_its_row_to_the_center(screen: Screen) -> None:
            press(screen, ShortcutId.TRACKER_NEXT_ROW, STEPS_DOWN)

            expect_centered(screen, CLICKED_ROW + STEPS_DOWN)
            assert tracker.has_caret(CLICKED_ROW + STEPS_DOWN, CHANNEL)

        def a_page_brings_its_row_to_the_center(screen: Screen) -> None:
            press(screen, ShortcutId.TRACKER_PAGE_DOWN, 1)

            row = screen.expect(
                lambda: tracker.caret_row(CHANNEL),
                lambda landed: landed is not None and landed > CLICKED_ROW + STEPS_DOWN,
                description="the caret a page further down",
            )
            assert row is not None
            expect_centered(screen, row)

        def the_last_row_reaches_the_center(screen: Screen) -> None:
            press(screen, ShortcutId.TRACKER_LAST_ROW, 1)

            expect_centered(screen, LAST_ROW)

        screen.scenario(
            a_click_leaves_the_grid_where_it_stands,
            a_step_brings_its_row_to_the_center,
            a_page_brings_its_row_to_the_center,
            the_last_row_reaches_the_center,
        ).run()


class TestTheRowsAroundTheFrame:
    """The rows beside the shown frame are the song's own, dimmed, and blank where the song ends.

    Above the first frame's first row the rows stand blank, and below its last row stand the next frame's
    first rows. Above the second frame's first row stand the first frame's last rows, dimmed beside the
    frame's own, and below its last the song has ended.
    """

    def test_the_song_reads_on_past_the_frame(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def the_first_frame_stands_below_blank_rows(screen: Screen) -> None:
            on_the_sequencer(screen)
            tracker.click(0, CHANNEL, SLOT)
            center_on_the_first_row(screen)

            assert tracker.numbers_above(NEIGHBORS) == (BLANK,) * NEIGHBORS

        def the_next_frame_stands_below_the_last_row(screen: Screen) -> None:
            press(screen, ShortcutId.TRACKER_LAST_ROW, 1)
            expect_centered(screen, LAST_ROW)

            assert tracker.numbers_below(NEIGHBORS) == FIRST_ROWS_OF_A_FRAME

        def the_second_frame_stands_below_the_first_frames_last_rows(screen: Screen) -> None:
            show_frame(screen, SECOND_FRAME)
            center_on_the_first_row(screen)

            assert tracker.numbers_above(NEIGHBORS) == LAST_ROWS_OF_A_FRAME
            assert alpha(tracker.number_color_above(1)) < alpha(tracker.number_color(0))
            assert tracker.numbers_below(NEIGHBORS) == (BLANK,) * NEIGHBORS

        screen.scenario(
            the_first_frame_stands_below_blank_rows,
            the_next_frame_stands_below_the_last_row,
            the_second_frame_stands_below_the_first_frames_last_rows,
        ).run()


class TestARowOfAnotherFrameTakesNoClick:
    """A click on a row beside the frame leaves the caret where it stood; a click on the frame's own row moves it."""

    def test_a_click_beside_the_frame_moves_nothing(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker

        def a_click_above_the_frame_leaves_the_caret(screen: Screen) -> None:
            on_the_sequencer(screen)
            show_frame(screen, SECOND_FRAME)
            center_on_the_first_row(screen)

            tracker.click_above(1, CHANNEL, SLOT)
            screen.frames(SETTLING_FRAMES)

            assert tracker.has_caret(0, CHANNEL)

        def a_click_on_the_frames_row_moves_the_caret(screen: Screen) -> None:
            tracker.click(1, CHANNEL, SLOT)

            screen.expect(lambda: tracker.has_caret(1, CHANNEL), bool, description="the caret moved")

        screen.scenario(
            a_click_above_the_frame_leaves_the_caret,
            a_click_on_the_frames_row_moves_the_caret,
        ).run()


class TestFollowRows:
    """While Follow rows plays the song, the sounding row stands at the middle of the band.

    The song plays from its start and pauses, which keeps the playhead's mark where it stood. Stopping takes
    the mark away, so the one tint stopping removes is the row that sounded, and it stood at the middle.
    """

    def test_the_sounding_row_stands_at_the_center(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        readings: List[PausedReading] = []

        def a_paused_song_holds_its_row_at_the_center(screen: Screen) -> None:
            on_the_sequencer(screen)
            screen.press_shortcut(ShortcutId.PLAY_FROM_START)
            expect_playing(screen)
            screen.frames(PLAYING_FRAMES)

            screen.press_shortcut(ShortcutId.PLAY)
            expect_paused(screen)
            screen.frames(SETTLING_FRAMES)

            center = tracker.centered_row()
            tinted = tracker.tinted_rows_in_view()
            assert center is not None
            assert center in tinted
            readings.append(PausedReading(center=center, tinted=tinted))

        def stopping_takes_the_mark_from_the_center(screen: Screen) -> None:
            screen.press_shortcut(ShortcutId.STOP)
            expect_stopped(screen)
            screen.frames(SETTLING_FRAMES)

            paused = readings[-1]
            assert paused.tinted - tracker.tinted_rows_in_view() <= {paused.center}

        screen.scenario(
            a_paused_song_holds_its_row_at_the_center,
            stopping_takes_the_mark_from_the_center,
        ).run()


class TestTheBandFollowsItsHeight:
    """Folding the card above the tracker makes the band taller, so more of the song stands either side.

    The row the caret stands on stays at the middle, and unfolding the card brings the band back.
    """

    def test_folding_the_order_card_widens_the_reach(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        order = screen.main.card(TAG_SEQUENCER_ORDER_WINDOW_ORDER_CARD)
        reach: List[int] = []

        def the_first_row_stands_at_the_center(screen: Screen) -> None:
            on_the_sequencer(screen)
            tracker.click(0, CHANNEL, SLOT)
            center_on_the_first_row(screen)
            reach.append(tracker.rows_above_the_frame())

        def a_folded_card_reaches_further(screen: Screen) -> None:
            order.toggle()
            screen.expect(order.is_collapsed, bool, description="the order card folded")

            screen.expect(tracker.rows_above_the_frame, lambda rows: rows > reach[0], description="a wider reach")
            expect_centered(screen, 0)

        def an_unfolded_card_reaches_as_before(screen: Screen) -> None:
            order.toggle()
            screen.expect(lambda: not order.is_collapsed(), bool, description="the order card unfolded")

            screen.expect(tracker.rows_above_the_frame, reach[0].__eq__, description="the reach as before")
            expect_centered(screen, 0)

        screen.scenario(
            the_first_row_stands_at_the_center,
            a_folded_card_reaches_further,
            an_unfolded_card_reaches_as_before,
        ).run()
