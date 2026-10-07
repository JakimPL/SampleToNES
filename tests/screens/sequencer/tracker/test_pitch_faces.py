from typing import Dict, Final

from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import NOTE_BLANK
from tests.screens.sequencer.tracker.constants import LINE_NUMBER, PIANO_C, SAMPLE_COLUMN, TYPING_FRAMES
from tests.screens.sequencer.tracker.steps import play_a_note, type_into
from tests.suite.screens.dearpygui.keys import IMGUI_LETTER_A
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from tests.suite.screens.worlds.songs import PAD_ROW

PIANO_D_UP: Final[int] = IMGUI_LETTER_A + ord("w") - ord("a")
STEP_TYPED: Final[str] = "03"
STEP_SHOWN: Final[str] = "+03"
DIGITS_TYPED: Final[str] = "22"
DIGITS_SHOWN: Final[str] = "+22"
C_AT_OCTAVE_TWO: Final[str] = "C-2"
D_ABOVE_THE_OCTAVE: Final[str] = "D-3"
PERIOD_OF_C: Final[str] = "0-#"
LINE_ROW: Final[int] = 0
DIGIT_ROW: Final[int] = 2
PLACED_ROW: Final[int] = 6


class TestThePitchCellTakesEitherFace:
    """A pitch cell takes a note or a step whatever voice its channel carries: the digit keys type a
    step, the piano keys a note, and the noise channel reads a note as one of its periods. The Sample
    column hands a note to the channels still playing the sample, each reading it its own way.
    """

    def test_steps_and_notes_land_in_any_column(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        history = screen.sequencer.history

        def pitches_at(row: int) -> Dict[ChannelName, str]:
            return {channel: tracker.label(row, channel, SubColumn.TRANSPOSE) for channel in ChannelName.items()}

        def a_step_lands_on_an_instrument(screen: Screen) -> None:
            on_the_sequencer(screen)

            type_into(screen, PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE, STEP_TYPED)

            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == STEP_SHOWN
            assert history.current().words.endswith(f"t {STEP_SHOWN}")

        def a_note_lands_on_a_sample(screen: Screen) -> None:
            play_a_note(screen, LINE_ROW, ChannelName.PULSE1, PIANO_C)

            assert tracker.label(LINE_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE) == C_AT_OCTAVE_TWO
            assert history.current().words.endswith(f"t {C_AT_OCTAVE_TWO}")

        def a_digit_types_a_step_and_the_key_beside_it_a_note(screen: Screen) -> None:
            type_into(screen, DIGIT_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE, DIGITS_TYPED)
            play_a_note(screen, DIGIT_ROW + 1, ChannelName.PULSE1, PIANO_D_UP)

            assert tracker.label(DIGIT_ROW, ChannelName.PULSE1, SubColumn.TRANSPOSE) == DIGITS_SHOWN
            assert tracker.label(DIGIT_ROW + 1, ChannelName.PULSE1, SubColumn.TRANSPOSE) == D_ABOVE_THE_OCTAVE

        def the_sample_column_hands_a_note_to_the_channels_playing(screen: Screen) -> None:
            type_into(screen, PLACED_ROW, SAMPLE_COLUMN, SubColumn.VOICE, LINE_NUMBER)
            tracker.click(PLACED_ROW + 1, SAMPLE_COLUMN, SubColumn.TRANSPOSE)

            screen.hand.press_key(PIANO_C, modifiers=[])
            screen.frames(TYPING_FRAMES)

            assert pitches_at(PLACED_ROW + 1) == {
                ChannelName.PULSE1: C_AT_OCTAVE_TWO,
                ChannelName.PULSE2: NOTE_BLANK,
                ChannelName.TRIANGLE: C_AT_OCTAVE_TWO,
                ChannelName.NOISE: PERIOD_OF_C,
            }

        def the_noise_channel_reads_a_note_as_a_period(screen: Screen) -> None:
            play_a_note(screen, PLACED_ROW + 2, ChannelName.NOISE, PIANO_C)

            assert tracker.label(PLACED_ROW + 2, ChannelName.NOISE, SubColumn.TRANSPOSE) == PERIOD_OF_C
            assert tracker.label(PLACED_ROW + 2, ChannelName.PULSE1, SubColumn.TRANSPOSE) == NOTE_BLANK

        screen.scenario(
            a_step_lands_on_an_instrument,
            a_note_lands_on_a_sample,
            a_digit_types_a_step_and_the_key_beside_it_a_note,
            the_sample_column_hands_a_note_to_the_channels_playing,
            the_noise_channel_reads_a_note_as_a_period,
            leave_letting_the_project_go,
        ).run()
