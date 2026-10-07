from functools import partial
from typing import Dict, Final

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import NOTE_BLANK, display_id
from tests.screens.sequencer.tracker.constants import (
    LINE_NUMBER,
    PAD_NUMBER,
    PIANO_C,
    SAMPLE_COLUMN,
    TYPING_FRAMES,
)
from tests.screens.sequencer.tracker.steps import play_a_note, type_into
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from tests.suite.screens.worlds.songs import LINE, PAD

LINE_POSITION: Final[int] = 0
PAD_POSITION: Final[int] = 2
EMPTY_VOICE: Final[str] = display_id(None)
C_AT_OCTAVE_TWO: Final[str] = "C-2"
PERIOD_OF_C: Final[str] = "0-#"
STEP_TYPED: Final[str] = "03"
STEP_SHOWN: Final[str] = "+03"
TYPED_ROW: Final[int] = 1
SAMPLE_ROW: Final[int] = 5
FREE_ROW: Final[int] = 7


class TestTheMarkedVoice:
    """A voice clicked in the Voices list stays marked while the grid has the caret, and every pitch typed
    there places it: a channel column takes either kind, and the Sample column takes a sample and writes
    the pitch alone for an instrument. The grid keeps the keys meanwhile, and a click below the list's
    rows ends the marking.
    """

    def test_pitches_carry_the_marked_voice(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        voices = screen.sequencer.voices

        def mark(name: str, position: int) -> None:
            row = screen.expect_item(partial(voices.row, name), description=f"the row of {name}")
            voices.pick(row)
            screen.expect(partial(voices.is_picked, position), bool, description=f"{name} marked")

        def pitches_at(row: int) -> Dict[ChannelName, str]:
            return {channel: tracker.label(row, channel, SubColumn.TRANSPOSE) for channel in ChannelName.items()}

        def a_note_places_the_marked_pad(screen: Screen) -> None:
            on_the_sequencer(screen)
            mark(PAD, PAD_POSITION)

            play_a_note(screen, TYPED_ROW, ChannelName.PULSE1, PIANO_C)

            assert tracker.label(TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE) == PAD_NUMBER
            assert tracker.label(TYPED_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE) == C_AT_OCTAVE_TWO
            assert tracker.has_caret(TYPED_ROW + 1, ChannelName.PULSE1)
            assert voices.is_picked(PAD_POSITION)

        def a_step_places_it_too(screen: Screen) -> None:
            type_into(screen, TYPED_ROW + 1, ChannelName.PULSE1, SubColumn.TRANSPOSE, STEP_TYPED)

            assert tracker.label(TYPED_ROW + 1, ChannelName.PULSE1, SubColumn.VOICE) == PAD_NUMBER
            assert tracker.label(TYPED_ROW + 1, ChannelName.PULSE1, SubColumn.TRANSPOSE) == STEP_SHOWN

        def a_marked_sample_fills_the_sample_column(screen: Screen) -> None:
            mark(LINE, LINE_POSITION)
            tracker.click(SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.TRANSPOSE)

            screen.hand.press_key(PIANO_C, modifiers=[])
            screen.frames(TYPING_FRAMES)

            assert tracker.label(SAMPLE_ROW, SAMPLE_COLUMN, SubColumn.VOICE) == LINE_NUMBER
            assert pitches_at(SAMPLE_ROW) == {
                ChannelName.PULSE1: C_AT_OCTAVE_TWO,
                ChannelName.PULSE2: NOTE_BLANK,
                ChannelName.TRIANGLE: C_AT_OCTAVE_TWO,
                ChannelName.NOISE: PERIOD_OF_C,
            }

        def a_marked_instrument_writes_the_pitch_alone_there(screen: Screen) -> None:
            mark(PAD, PAD_POSITION)
            tracker.click(SAMPLE_ROW + 1, SAMPLE_COLUMN, SubColumn.TRANSPOSE)

            screen.hand.press_key(PIANO_C, modifiers=[])
            screen.frames(TYPING_FRAMES)

            assert tracker.label(SAMPLE_ROW + 1, SAMPLE_COLUMN, SubColumn.VOICE) == EMPTY_VOICE
            assert pitches_at(SAMPLE_ROW + 1) == {
                ChannelName.PULSE1: C_AT_OCTAVE_TWO,
                ChannelName.PULSE2: NOTE_BLANK,
                ChannelName.TRIANGLE: C_AT_OCTAVE_TWO,
                ChannelName.NOISE: PERIOD_OF_C,
            }

        def the_grid_keeps_the_delete_key(screen: Screen) -> None:
            names = voices.names()
            tracker.click(TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE)

            screen.press_shortcut(ShortcutId.TRACKER_CLEAR_ROW)

            screen.expect(
                partial(tracker.label, TYPED_ROW, ChannelName.PULSE1, SubColumn.VOICE),
                EMPTY_VOICE.__eq__,
                description="the cell cleared",
            )
            assert voices.names() == names
            assert not voices.remove_prompt.is_shown()
            assert voices.is_picked(PAD_POSITION)

        def a_click_below_the_rows_ends_the_marking(screen: Screen) -> None:
            voices.click_below_the_rows()
            screen.expect(lambda: not voices.is_picked(PAD_POSITION), bool, description="the mark cleared")

            play_a_note(screen, FREE_ROW, ChannelName.PULSE2, PIANO_C)

            assert tracker.label(FREE_ROW, ChannelName.PULSE2, SubColumn.VOICE) == EMPTY_VOICE
            assert tracker.label(FREE_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == C_AT_OCTAVE_TWO

        screen.scenario(
            a_note_places_the_marked_pad,
            a_step_places_it_too,
            a_marked_sample_fills_the_sample_column,
            a_marked_instrument_writes_the_pitch_alone_there,
            the_grid_keeps_the_delete_key,
            a_click_below_the_rows_ends_the_marking,
            leave_letting_the_project_go,
        ).run()
