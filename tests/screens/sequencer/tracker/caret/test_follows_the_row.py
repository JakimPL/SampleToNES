from functools import partial
from typing import List

from automation.screen import Screen
from automation.steps.sequencer import on_the_sequencer
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from tests.screens.sequencer.tracker.caret.constants import (
    BURST,
    CHANNEL,
    CLICKED_ROW,
    LANDING_FRAMES,
    QUIET_FRAMES,
    SLOT,
)
from tests.screens.sequencer.tracker.caret.steps import Drawing, frames_apart, read_drawing


class TestTheCaretFollowsTheRow:
    """A key that carries the caret to another row draws the caret and the cursor's cell on that row from the frame
    the grid re-centers on, with no frame drawing the two a row apart.

    Every frame between the press and the landing is read: the caret's mark and the highlighted
    row set for the next frame, against the row tops that next frame draws. A step down, a burst
    of steps, and a step back up are walked, and a step along the row, which asks for no scroll,
    ends the run with the caret where it stood.
    """

    def test_the_mark_stands_on_the_cursor_row_on_every_frame(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        reading = partial(read_drawing, screen, CHANNEL, SLOT)

        def frames_of(shortcut: ShortcutId, times: int) -> List[Drawing]:
            with screen.record(reading) as recording:
                screen.frames(QUIET_FRAMES)
                for _ in range(times):
                    screen.press_shortcut(shortcut)
                screen.frames(LANDING_FRAMES)

            return recording.values()

        def expect_landed(drawings: List[Drawing], row: int) -> None:
            assert drawings[-1].cursor_row == row
            assert frames_apart(drawings) == []

        def a_step_down_lands_as_one(screen: Screen) -> None:
            on_the_sequencer(screen)
            tracker.click(CLICKED_ROW, CHANNEL, SLOT)
            screen.expect(lambda: tracker.has_caret(CLICKED_ROW, CHANNEL), bool, description="the caret clicked in")

            drawings = frames_of(ShortcutId.TRACKER_NEXT_ROW, 1)

            expect_landed(drawings, CLICKED_ROW + 1)
            assert any(drawing.cursor_row == CLICKED_ROW for drawing in drawings)

        def a_burst_of_steps_lands_each_as_one(screen: Screen) -> None:
            drawings = frames_of(ShortcutId.TRACKER_NEXT_ROW, BURST)

            expect_landed(drawings, CLICKED_ROW + 1 + BURST)

        def a_step_up_lands_as_one(screen: Screen) -> None:
            drawings = frames_of(ShortcutId.TRACKER_PREVIOUS_ROW, 1)

            expect_landed(drawings, CLICKED_ROW + BURST)

        def a_step_along_the_row_keeps_the_rows_still(screen: Screen) -> None:
            drawings = frames_of(ShortcutId.TRACKER_NEXT_SUBCOLUMN, 1)

            expect_landed(drawings, CLICKED_ROW + BURST)
            assert len({tuple(sorted(drawing.row_tops.items())) for drawing in drawings}) == 1

        screen.scenario(
            a_step_down_lands_as_one,
            a_burst_of_steps_lands_each_as_one,
            a_step_up_lands_as_one,
            a_step_along_the_row_keeps_the_rows_still,
        ).run()
