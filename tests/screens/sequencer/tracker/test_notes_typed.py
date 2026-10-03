from functools import partial
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import NOTE_BLANK
from tests.screens.sequencer.tracker.constants import LINE_NUMBER, PAD_NUMBER, PIANO_C, SAMPLE_COLUMN, TYPING_FRAMES
from tests.screens.sequencer.tracker.steps import play_a_note, type_into
from tests.suite.screens.dearpygui.items.texts import read_label
from tests.suite.screens.dearpygui.keys import IMGUI_LETTER_A
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from tests.suite.screens.views.tracker import tracker_cell, tracker_cell_theme
from tests.suite.screens.vocabulary.playback import PAUSE
from tests.suite.screens.worlds.songs import PAD_ROW

PIANO_C_UP: Final[int] = IMGUI_LETTER_A + ord("q") - ord("a")
NOTE_AT_OCTAVE_TWO: Final[str] = "C-2"
NOTE_AT_OCTAVE_THREE: Final[str] = "C-3"
NOTE_AT_OCTAVE_FOUR: Final[str] = "C-4"
HIGHER_OCTAVE: Final[int] = 3
NO_VOICE_ROW: Final[int] = 2


def history_size(screen: Screen) -> int:
    """The number of lines in the Sequencer's history."""
    return len(screen.sequencer.history.lines())


class TestNotesTypedPianoStyle:
    """A note key writes the note at the octave in force into a pitch slot whose channel carries a voice.

    The noise column, a voice slot and a row whose channel carries no voice stay blank, and the history
    stays as it was for them.
    """

    def test_notes_land_where_a_voice_plays_and_nowhere_else(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        history = screen.sequencer.history

        def a_note_lands_at_the_octave_in_force(screen: Screen) -> None:
            on_the_sequencer(screen)
            assert tracker.octave() == 2
            before = history_size(screen)

            play_a_note(screen, PAD_ROW, ChannelName.PULSE2, PIANO_C)

            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == NOTE_AT_OCTAVE_TWO
            assert tracker.has_caret(PAD_ROW + 1, ChannelName.PULSE2)
            assert history_size(screen) == before + 1
            assert history.current().words.endswith(f"t {NOTE_AT_OCTAVE_TWO}")

        def a_new_octave_lands_an_octave_up(screen: Screen) -> None:
            tracker.raise_octave()
            screen.expect(tracker.octave, HIGHER_OCTAVE.__eq__, description="the octave raised")

            play_a_note(screen, PAD_ROW, ChannelName.PULSE2, PIANO_C)
            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == NOTE_AT_OCTAVE_THREE

            play_a_note(screen, PAD_ROW, ChannelName.PULSE2, PIANO_C_UP)
            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == NOTE_AT_OCTAVE_FOUR

        def the_noise_column_takes_no_note(screen: Screen) -> None:
            type_into(screen, NO_VOICE_ROW, ChannelName.NOISE, SubColumn.VOICE, PAD_NUMBER)
            assert tracker.label(NO_VOICE_ROW, ChannelName.NOISE, SubColumn.VOICE) == PAD_NUMBER
            before = history_size(screen)

            play_a_note(screen, NO_VOICE_ROW, ChannelName.NOISE, PIANO_C)

            assert tracker.label(NO_VOICE_ROW, ChannelName.NOISE, SubColumn.TRANSPOSE) == NOTE_BLANK
            assert history_size(screen) == before

        def the_voice_slot_takes_no_note(screen: Screen) -> None:
            before = history_size(screen)
            tracker.click(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)

            screen.hand.press_key(PIANO_C, modifiers=[])
            screen.frames(TYPING_FRAMES)

            assert tracker.label(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE) == PAD_NUMBER
            assert history_size(screen) == before

        def a_row_carrying_no_voice_records_nothing(screen: Screen) -> None:
            before = history_size(screen)

            play_a_note(screen, NO_VOICE_ROW, ChannelName.PULSE2, PIANO_C)

            assert tracker.label(NO_VOICE_ROW, ChannelName.PULSE2, SubColumn.TRANSPOSE) == NOTE_BLANK
            assert tracker.has_caret(NO_VOICE_ROW + 1, ChannelName.PULSE2)
            assert history_size(screen) == before

        def a_note_where_the_voice_plays_on_lands(screen: Screen) -> None:
            before = history_size(screen)

            play_a_note(screen, PAD_ROW + 1, ChannelName.PULSE2, PIANO_C)

            assert tracker.label(PAD_ROW + 1, ChannelName.PULSE2, SubColumn.TRANSPOSE) == NOTE_AT_OCTAVE_THREE
            assert history_size(screen) == before + 1

        screen.scenario(
            a_note_lands_at_the_octave_in_force,
            a_new_octave_lands_an_octave_up,
            the_noise_column_takes_no_note,
            the_voice_slot_takes_no_note,
            a_row_carrying_no_voice_records_nothing,
            a_note_where_the_voice_plays_on_lands,
            leave_letting_the_project_go,
        ).run()


class TestAVoiceTyped:
    """A voice number typed into a slot arrives with its kind's color in the same frame.

    An instrument typed into the Sample column keeps the number and the color as they were.
    """

    def test_the_color_comes_with_the_number(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        typed_row = 9

        def cell_in_frame(row: int, channel: Optional[ChannelName]) -> Tuple[str, Optional[int]]:
            return read_label(tracker_cell(row, channel, SubColumn.VOICE)), tracker_cell_theme(
                row, channel, SubColumn.VOICE
            )

        def frames_while_typing(row: int, channel: Optional[ChannelName], text: str) -> List[Tuple[str, Optional[int]]]:
            tracker.click(row, channel, SubColumn.VOICE)
            with screen.record(partial(cell_in_frame, row, channel)) as recording:
                screen.hand.type_text(text)
                screen.frames(TYPING_FRAMES)

            return recording.values()

        def an_instrument_arrives_in_its_color(screen: Screen) -> None:
            on_the_sequencer(screen)
            instrument = tracker.theme(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)

            frames = frames_while_typing(typed_row, ChannelName.PULSE1, PAD_NUMBER)

            numbered = [theme for label, theme in frames if label == PAD_NUMBER]
            assert numbered
            assert all(theme == instrument for theme in numbered)

        def a_sample_arrives_in_its_color(screen: Screen) -> None:
            sample = screen.sequencer.tracker.theme(0, ChannelName.PULSE1, SubColumn.VOICE)

            frames = frames_while_typing(typed_row + 2, ChannelName.PULSE1, LINE_NUMBER)

            numbered = [theme for label, theme in frames if label == LINE_NUMBER]
            assert numbered
            assert all(theme == sample for theme in numbered)

        def an_instrument_in_the_sample_column_changes_nothing(screen: Screen) -> None:
            standing = tracker.label(typed_row, SAMPLE_COLUMN, SubColumn.VOICE), tracker.theme(
                typed_row, SAMPLE_COLUMN, SubColumn.VOICE
            )
            before = history_size(screen)

            frames = frames_while_typing(typed_row, SAMPLE_COLUMN, PAD_NUMBER)

            assert all(frame[1] == standing[1] for frame in frames)
            assert all(frame[0] != PAD_NUMBER for frame in frames)
            assert tracker.label(typed_row, SAMPLE_COLUMN, SubColumn.VOICE) == standing[0]
            assert history_size(screen) == before

        screen.scenario(
            an_instrument_arrives_in_its_color,
            a_sample_arrives_in_its_color,
            an_instrument_in_the_sample_column_changes_nothing,
            leave_letting_the_project_go,
        ).run()


class TestPlayingFromATrackerRow:
    """Playing the song from the caret's row reads as playing in the Playback menu, Stop answering."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: playing from a tracker row leaves the Playback menu reading Play",
    )
    def test_the_menu_follows(self, screen: Screen) -> None:
        """After the play-from-row shortcut, the Playback menu offers Pause and Stop answers."""
        on_the_sequencer(screen)
        screen.sequencer.tracker.click(1, ChannelName.PULSE1, SubColumn.VOICE)

        screen.press_shortcut(ShortcutId.TRACKER_PLAY_FROM_ROW)

        screen.expect(screen.sequencer.playback.can_stop, bool, description="Stop answering")
        assert screen.sequencer.playback.play_entry() == screen.words(PAUSE)
