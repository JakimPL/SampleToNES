import operator
from functools import partial
from typing import Final, List, Optional, Tuple

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import BLANK, NOTE_BLANK, NOTE_OFF
from tests.suite.screens.application import Startup
from tests.suite.screens.dearpygui.items import read_label
from tests.suite.screens.dearpygui.keys import IMGUI_LETTER_A
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go
from tests.suite.screens.views.tracker import tracker_cell, tracker_cell_theme
from tests.suite.screens.vocabulary.playback import PAUSE
from tests.suite.screens.world import ARRANGED_PROJECT, BASS_ROW, PAD_ROW

PIANO_C: Final[int] = IMGUI_LETTER_A + ord("z") - ord("a")
PIANO_C_UP: Final[int] = IMGUI_LETTER_A + ord("q") - ord("a")
TYPING_FRAMES: Final[int] = 10
EMPTY_VOICE: Final[str] = ".."
LINE_NUMBER: Final[str] = "00"
BASS_NUMBER: Final[str] = "01"
PAD_NUMBER: Final[str] = "02"
NOTE_AT_OCTAVE_TWO: Final[str] = "C-2"
NOTE_AT_OCTAVE_THREE: Final[str] = "C-3"
NOTE_AT_OCTAVE_FOUR: Final[str] = "C-4"
HIGHER_OCTAVE: Final[int] = 3
NO_VOICE_ROW: Final[int] = 2
SAMPLE_COLUMN: Final[Optional[ChannelName]] = None
SAMPLE_HEADER: Final[str] = "sequencer.tracker.label.column_sample"
SET_VOICE: Final[str] = "sequencer.tracker.label.context_set_voice"
CLEAR_SUBCOLUMN: Final[str] = "sequencer.tracker.label.context_clear_subcolumn"
SUBCOLUMN_LETTERS: Final[Tuple[Tuple[SubColumn, str], ...]] = (
    (SubColumn.VOICE, "n"),
    (SubColumn.TRANSPOSE, "t"),
    (SubColumn.VOLUME, "v"),
)
EVERY_CHANNEL: Final[Tuple[ChannelName, ...]] = tuple(ChannelName.items())
LINE_CHANNELS: Final[Tuple[ChannelName, ...]] = (ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE)


def history_size(screen: Screen) -> int:
    return len(screen.sequencer.history.lines())


def on_the_sequencer(screen: Screen) -> None:
    screen.tabs.bring_to_front(Tab.SEQUENCER)
    screen.expect(screen.sequencer.voices.names, bool, description="the project's voices")


def play_a_note(screen: Screen, row: int, channel: ChannelName, key: int) -> None:
    screen.sequencer.tracker.click(row, channel, SubColumn.TRANSPOSE)
    screen.hand.press_key(key, modifiers=[])
    screen.frames(TYPING_FRAMES)


def type_into(screen: Screen, row: int, channel: Optional[ChannelName], subcolumn: SubColumn, text: str) -> None:
    screen.sequencer.tracker.click(row, channel, subcolumn)
    screen.hand.type_text(text)
    screen.frames(TYPING_FRAMES)


@pytest.fixture
def startup() -> Startup:
    return Startup(reconstruction=None, project=ARRANGED_PROJECT)


class TestNotesTypedPianoStyle:
    """A note key writes the note at the octave in force into a pitch slot whose channel carries a voice.

    The noise column, a voice slot and a row carrying no voice take no note, and nothing reaches the
    history for them.
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

    An instrument typed into the Sample column leaves both the number and the color as they were.
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


class TestTheSampleColumn:
    """The Sample column reads Sample, offers samples alone, and reads a row by the samples its channels play."""

    def test_its_header_its_menu_and_its_readings(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        menu = screen.context_menu
        cut_row = 6
        instrument_row = 2

        def the_header_reads_sample(screen: Screen) -> None:
            on_the_sequencer(screen)

            assert tracker.header(SAMPLE_COLUMN) == screen.words(SAMPLE_HEADER)

        def set_voice_offers_samples_alone(screen: Screen) -> None:
            tracker.right_click(1, SAMPLE_COLUMN, SubColumn.VOICE)
            screen.expect(menu.is_shown, bool, description="the cell's menu")

            offered = menu.submenu(screen.words(SET_VOICE))

            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")
            assert [enabled for _, enabled in offered] == [True, True, False]

        def a_channel_cell_offers_every_voice(screen: Screen) -> None:
            tracker.right_click(1, ChannelName.PULSE2, SubColumn.VOICE)
            screen.expect(menu.is_shown, bool, description="the cell's menu")

            offered = menu.submenu(screen.words(SET_VOICE))

            menu.dismiss()
            screen.expect(menu.is_shown, operator.not_, description="the menu put away")
            assert len(offered) == len(screen.sequencer.voices.names())
            assert all(enabled for _, enabled in offered)

        def an_instrument_alone_reads_empty(screen: Screen) -> None:
            type_into(screen, instrument_row, ChannelName.PULSE1, SubColumn.VOICE, PAD_NUMBER)

            assert tracker.label(instrument_row, ChannelName.PULSE1, SubColumn.VOICE) == PAD_NUMBER
            assert tracker.label(instrument_row, SAMPLE_COLUMN, SubColumn.VOICE) == EMPTY_VOICE

        def a_row_cut_everywhere_reads_the_cut(screen: Screen) -> None:
            for channel in EVERY_CHANNEL:
                type_into(screen, cut_row, channel, SubColumn.VOICE, "-")

            assert all(tracker.label(cut_row, channel, SubColumn.VOICE) == NOTE_OFF for channel in EVERY_CHANNEL)
            assert tracker.label(cut_row, SAMPLE_COLUMN, SubColumn.VOICE) == NOTE_OFF

        def the_bass_alone_reads_as_itself(screen: Screen) -> None:
            assert screen.sequencer.tracker.label(BASS_ROW, SAMPLE_COLUMN, SubColumn.VOICE) == BASS_NUMBER

        screen.scenario(
            the_header_reads_sample,
            set_voice_offers_samples_alone,
            a_channel_cell_offers_every_voice,
            an_instrument_alone_reads_empty,
            a_row_cut_everywhere_reads_the_cut,
            the_bass_alone_reads_as_itself,
            leave_letting_the_project_go,
        ).run()

    def test_a_volume_lands_where_the_sample_still_plays(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        placed_row = 1

        def place_the_line_across_its_channels(screen: Screen) -> None:
            on_the_sequencer(screen)

            type_into(screen, placed_row, SAMPLE_COLUMN, SubColumn.VOICE, LINE_NUMBER)

            assert [tracker.label(placed_row, channel, SubColumn.VOICE) for channel in LINE_CHANNELS] == [
                LINE_NUMBER
            ] * 3
            assert tracker.label(placed_row, SAMPLE_COLUMN, SubColumn.VOICE) == LINE_NUMBER

        def a_volume_reaches_every_channel_it_plays(screen: Screen) -> None:
            type_into(screen, placed_row + 1, SAMPLE_COLUMN, SubColumn.VOLUME, "8")

            assert {channel: tracker.label(placed_row + 1, channel, SubColumn.VOLUME) for channel in EVERY_CHANNEL} == {
                ChannelName.PULSE1: "8",
                ChannelName.PULSE2: BLANK,
                ChannelName.TRIANGLE: "8",
                ChannelName.NOISE: "8",
            }

        def a_channel_cut_stops_taking_it(screen: Screen) -> None:
            type_into(screen, placed_row + 2, ChannelName.NOISE, SubColumn.VOICE, "-")

            type_into(screen, placed_row + 3, SAMPLE_COLUMN, SubColumn.VOLUME, "9")

            assert {channel: tracker.label(placed_row + 3, channel, SubColumn.VOLUME) for channel in EVERY_CHANNEL} == {
                ChannelName.PULSE1: "9",
                ChannelName.PULSE2: BLANK,
                ChannelName.TRIANGLE: "9",
                ChannelName.NOISE: BLANK,
            }

        def a_channel_given_an_instrument_stops_taking_it(screen: Screen) -> None:
            type_into(screen, placed_row + 4, ChannelName.TRIANGLE, SubColumn.VOICE, PAD_NUMBER)

            type_into(screen, placed_row + 5, SAMPLE_COLUMN, SubColumn.VOLUME, "A")

            assert {channel: tracker.label(placed_row + 5, channel, SubColumn.VOLUME) for channel in EVERY_CHANNEL} == {
                ChannelName.PULSE1: "A",
                ChannelName.PULSE2: BLANK,
                ChannelName.TRIANGLE: BLANK,
                ChannelName.NOISE: BLANK,
            }

        screen.scenario(
            place_the_line_across_its_channels,
            a_volume_reaches_every_channel_it_plays,
            a_channel_cut_stops_taking_it,
            a_channel_given_an_instrument_stops_taking_it,
            leave_letting_the_project_go,
        ).run()


class TestABlockPastedOnTheSampleColumn:
    """A block holding an instrument pasted onto the Sample column lands everything but the instrument's cells."""

    def test_the_instrument_is_passed_over(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        anchor = 9

        def copy_an_instrument_and_a_sample(screen: Screen) -> None:
            on_the_sequencer(screen)
            type_into(screen, PAD_ROW + 1, ChannelName.PULSE2, SubColumn.VOICE, LINE_NUMBER)
            tracker.click(PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE)
            tracker.shift_click(PAD_ROW + 1, ChannelName.PULSE2, SubColumn.VOICE)

            screen.press_shortcut(ShortcutId.TRACKER_COPY_BLOCK)

        def paste_it_on_the_sample_column(screen: Screen) -> None:
            tracker.click(anchor, SAMPLE_COLUMN, SubColumn.VOICE)

            screen.press_shortcut(ShortcutId.TRACKER_PASTE_BLOCK)

            screen.expect(
                partial(tracker.label, anchor + 1, SAMPLE_COLUMN, SubColumn.VOICE),
                LINE_NUMBER.__eq__,
                description="the sample landed",
            )
            assert tracker.label(anchor, SAMPLE_COLUMN, SubColumn.VOICE) == EMPTY_VOICE
            assert all(tracker.label(anchor, channel, SubColumn.VOICE) != PAD_NUMBER for channel in EVERY_CHANNEL)

        screen.scenario(
            copy_an_instrument_and_a_sample, paste_it_on_the_sample_column, leave_letting_the_project_go
        ).run()


class TestHistoryLinesNameTheSlot:
    """A history line clearing a slot names it n for the voice, t for the transpose and v for the volume."""

    def test_each_slot_has_its_letter(self, screen: Screen) -> None:
        tracker = screen.sequencer.tracker
        history = screen.sequencer.history
        menu = screen.context_menu
        letters: List[str] = []

        def clear_each_slot_of_the_pad(screen: Screen) -> None:
            on_the_sequencer(screen)
            play_a_note(screen, PAD_ROW, ChannelName.PULSE2, PIANO_C)
            type_into(screen, PAD_ROW, ChannelName.PULSE2, SubColumn.VOLUME, "9")

            for subcolumn, _ in reversed(SUBCOLUMN_LETTERS):
                tracker.right_click(PAD_ROW, ChannelName.PULSE2, subcolumn)
                screen.expect(menu.is_shown, bool, description="the cell's menu")
                menu.choose(screen.words(CLEAR_SUBCOLUMN))
                screen.expect(menu.is_shown, operator.not_, description="the menu answered")
                screen.frames(TYPING_FRAMES)
                letters.append(history.current().words)

            for line, (_, letter) in zip(letters, reversed(SUBCOLUMN_LETTERS)):
                assert letter in line.split()

            assert len(set(letters)) == len(SUBCOLUMN_LETTERS)

        screen.scenario(clear_each_slot_of_the_pad, leave_letting_the_project_go).run()


class TestPlayingFromATrackerRow:
    """Playing the song from the caret's row reads as playing in the Playback menu, Stop answering."""

    @pytest.mark.xfail(
        strict=True,
        raises=AssertionError,
        reason="bugs-and-todos § Bugs: playing from a tracker row leaves the Playback menu reading Play",
    )
    def test_the_menu_follows(self, screen: Screen) -> None:
        on_the_sequencer(screen)
        screen.sequencer.tracker.click(1, ChannelName.PULSE1, SubColumn.VOICE)

        screen.press_shortcut(ShortcutId.TRACKER_PLAY_FROM_ROW)

        screen.expect(screen.sequencer.playback.can_stop, bool, description="Stop answering")
        assert screen.sequencer.playback.play_entry() == screen.words(PAUSE)
