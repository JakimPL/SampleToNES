import operator
from functools import partial
from typing import Optional, Sequence, Tuple

import numpy as np

from automation.dearpygui.geometry import Rect
from automation.dearpygui.items.reading import read_item
from automation.dearpygui.keys import IMGUI_ESCAPE
from automation.screen import Screen
from automation.steps.sequencer import on_the_sequencer
from automation.views.tracker import tracker_cell
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from tests.screens.sequencer.tracker.caret.constants import (
    CHANNEL,
    FIRST_CHARACTER,
    FIRST_POSITION,
    SECOND_CHARACTER,
    SLOT,
    TYPED_DIGIT,
    TYPING_FRAMES,
)
from tests.screens.sequencer.tracker.caret.steps import glyph_bottom, glyph_runs
from tests.suite.screens.worlds.songs import PAD_ROW

Color = Tuple[float, ...]


def under_run(mark: Rect, run: Tuple[int, int]) -> bool:
    """Whether the glyph drawn over the columns ``run`` lies inside the mark's span."""
    first, last = run
    return mark.x <= first and last < mark.x + mark.width


class TestTheMarkStandsUnderItsCharacter:
    """The caret's mark spans exactly the character it marks, from that character's left edge, under the glyph.

    The frame's pixels say where each glyph of the cell stands. The mark is read on the first
    character of a voice, on the second once a digit is typed, and on the order grid's first
    position, and a glyph the mark is set beside stays outside it.
    """

    def test_the_mark_spans_the_marked_glyph_alone(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        order = screen.sequencer.order

        def mark_and_glyphs(cell: Rect, color: Optional[Color]) -> Tuple[Rect, Sequence[Tuple[int, int]], int]:
            assert color is not None
            pixels = screen.frame_pixels()
            mark = tracker.caret_box()
            assert mark is not None
            return mark, glyph_runs(pixels, cell, color), glyph_bottom(pixels, cell, color)

        def tracker_cell_box(row: int, channel: ChannelName, slot: SubColumn) -> Rect:
            rect = screen.bridge.ask(lambda: read_item(tracker_cell(row, channel, slot)).rect)
            assert rect is not None
            return rect

        def the_first_character_of_a_voice(screen: Screen) -> None:
            on_the_sequencer(screen)
            tracker.click(PAD_ROW, CHANNEL, SLOT)
            screen.expect(lambda: tracker.has_caret(PAD_ROW, CHANNEL), bool, description="the caret clicked in")

            mark, runs, bottom = mark_and_glyphs(
                tracker_cell_box(PAD_ROW, CHANNEL, SLOT),
                tracker.text_color(PAD_ROW, CHANNEL, SLOT),
            )

            assert len(runs) == 2
            assert under_run(mark, runs[FIRST_CHARACTER])
            assert not under_run(mark, runs[SECOND_CHARACTER])
            assert runs[SECOND_CHARACTER][0] >= mark.x + mark.width
            assert mark.y >= bottom

        def the_second_character_once_a_digit_is_typed(screen: Screen) -> None:
            screen.hand.type_text(TYPED_DIGIT)
            screen.frames(TYPING_FRAMES)
            screen.expect(
                partial(tracker.label, PAD_ROW, CHANNEL, SLOT),
                operator.methodcaller("startswith", TYPED_DIGIT),
                description="the typed digit pending",
            )

            mark, runs, _ = mark_and_glyphs(
                tracker_cell_box(PAD_ROW, CHANNEL, SLOT),
                tracker.text_color(PAD_ROW, CHANNEL, SLOT),
            )

            assert len(runs) == 2
            assert under_run(mark, runs[SECOND_CHARACTER])
            assert not under_run(mark, runs[FIRST_CHARACTER])

            screen.hand.press_key(IMGUI_ESCAPE, modifiers=[])
            screen.frames(TYPING_FRAMES)

        def the_order_grids_first_position(screen: Screen) -> None:
            order.click(CHANNEL, FIRST_POSITION)
            screen.expect(lambda: not tracker.has_caret(PAD_ROW, CHANNEL), bool, description="the caret handed over")

            cell = order.cell_box(CHANNEL, FIRST_POSITION)
            assert cell is not None
            mark, runs, bottom = mark_and_glyphs(cell, order.text_color(CHANNEL, FIRST_POSITION))

            assert len(runs) == 2
            assert under_run(mark, runs[FIRST_CHARACTER])
            assert not under_run(mark, runs[SECOND_CHARACTER])
            assert mark.y >= bottom

        screen.scenario(
            the_first_character_of_a_voice,
            the_second_character_once_a_digit_is_typed,
            the_order_grids_first_position,
        ).run()
