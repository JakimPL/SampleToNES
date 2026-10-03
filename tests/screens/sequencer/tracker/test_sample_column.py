import operator
from functools import partial
from typing import Final, List, Tuple

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import BLANK, NOTE_OFF
from tests.screens.sequencer.tracker.constants import LINE_NUMBER, PAD_NUMBER, PIANO_C, SAMPLE_COLUMN, TYPING_FRAMES
from tests.screens.sequencer.tracker.steps import play_a_note, type_into
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import leave_letting_the_project_go, on_the_sequencer
from tests.suite.screens.worlds.songs import BASS_ROW, PAD_ROW

EMPTY_VOICE: Final[str] = ".."
BASS_NUMBER: Final[str] = "01"
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


class TestTheSampleColumn:
    """The Sample column reads Sample, offers only samples, and reads a row by the samples its channels play."""

    def test_its_header_its_menu_and_its_readings(self, screen: Screen) -> None:
        """The header, the Set voice menu and the readings of an instrument, a cut and a bass row follow
        the column's rule.
        """
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
        """A volume typed into the Sample column reaches the channels that still play the sample.

        A channel cut or given an instrument on its own is left out.
        """
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
    """A block holding an instrument pasted onto the Sample column lands its samples and leaves the instrument's cells empty."""

    def test_the_instrument_is_passed_over(self, screen: Screen) -> None:
        """The pasted sample appears below the anchor, and no cell takes the instrument's number."""
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
        """Clearing the volume, the transpose and the voice of one cell in turn gives three history lines,
        each with its own letter.
        """
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
