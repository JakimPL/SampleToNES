import operator
from functools import partial
from typing import Final, List, Optional, Tuple

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_application.utils.palette.palette import Palette
from sampletones_application.view_model.sequencer.subcolumn import SubColumn
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import NOTE_OFF
from tests.suite.screens.dearpygui.items.colors import rounded_color
from tests.suite.screens.palettes import Color, shipped_palettes, token_color
from tests.suite.screens.screen import Screen
from tests.suite.screens.steps.sequencer import forgive_the_hover_race, leave_letting_the_project_go
from tests.suite.screens.views.history import HistoryLine
from tests.suite.screens.worlds.songs import BASS_ROW, BASS_VOICE, LINE, PAD, PAD_ROW

SAMPLE_TOKEN: Final[str] = "voice_sample"
INSTRUMENT_TOKEN: Final[str] = "voice_instrument"
NEUTRAL_TOKEN: Final[str] = "text_disabled"
CUT_KEY: Final[str] = "-"
FIRST_ROW: Final[int] = 0
EMPTY_ROW: Final[int] = 1
CUT_ROW: Final[int] = 2
PLACED_ROW: Final[int] = 3
TYPING_FRAMES: Final[int] = 10
SETTLING_FRAMES: Final[int] = 10
RGB: Final[int] = 3
ALPHA: Final[int] = 3
LINE_NUMBER: Final[str] = "00"
FIRST_NUMBER: Final[str] = "01"
PAD_NUMBER: Final[str] = "02"
POSITION_MARK: Final[str] = ":"


def type_into(screen: Screen, row: int, channel: ChannelName, text: str) -> None:
    """Clicks the voice slot of a channel at a row, types the text and lets the typing settle."""
    screen.sequencer.tracker.click(row, channel, SubColumn.VOICE)
    screen.hand.type_text(text)
    screen.frames(TYPING_FRAMES)


def kind_mark(screen: Screen, voice: str) -> Color:
    """The rounded color of the kind mark beside the voice called ``voice`` in the list."""
    return rounded_color(screen.sequencer.voices.kind_color(voice))


def voice_color(screen: Screen, row: int, channel: ChannelName) -> Optional[Color]:
    """The text color of a channel's voice cell at a row, or None when the cell shows none."""
    return screen.sequencer.tracker.text_color(row, channel, SubColumn.VOICE)


def position_color(line: HistoryLine, position: str) -> Color:
    """The color of the piece of ``line`` naming a voice by its ``position``."""
    return rounded_color(
        next(segment.color for segment in line.segments if segment.words.rstrip(POSITION_MARK) == position)
    )


def is_dimmed(color: Optional[Color], full: Color) -> bool:
    """Whether ``color`` is ``full`` dimmed: the same hue, drawn fainter."""
    return color is not None and color[:RGB] == full[:RGB] and color[ALPHA] < full[ALPHA]


class TestKindColorsInEveryPalette:
    """A recording reads in the sample color and a hand-written voice in the instrument color, as kind marks and as tracker cells, in every palette and live on a swap.

    An empty cell and a cut read neutral, and a muted channel's cells keep their hue, fainter. The scenario cuts a cell and mutes the triangle, then checks the default palette and every shipped palette in Display settings.
    """

    def test_marks_and_cells_take_every_palette(self, screen: Screen) -> None:
        """Marks and cells take the colors of each palette as it is chosen."""
        tracker = screen.sequencer.tracker
        settings = screen.display_settings
        catalog = shipped_palettes()

        def cut_a_cell_and_mute_the_triangle(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            sample = token_color(catalog.get(DEFAULT_PALETTE_NAME), SAMPLE_TOKEN)
            assert voice_color(screen, BASS_ROW, ChannelName.TRIANGLE) == sample

            type_into(screen, CUT_ROW, ChannelName.PULSE1, CUT_KEY)
            tracker.click_header(ChannelName.TRIANGLE)

            screen.expect(
                partial(tracker.label, CUT_ROW, ChannelName.PULSE1, SubColumn.VOICE),
                NOTE_OFF.__eq__,
                description="the cut",
            )
            screen.expect(
                partial(voice_color, screen, BASS_ROW, ChannelName.TRIANGLE),
                partial(is_dimmed, full=sample),
                description="the muted triangle's cell dimmed",
            )

        def painted_in(screen: Screen, palette: Palette) -> None:
            sample = token_color(palette, SAMPLE_TOKEN)
            instrument = token_color(palette, INSTRUMENT_TOKEN)
            neutral = token_color(palette, NEUTRAL_TOKEN)

            assert kind_mark(screen, LINE) == sample
            assert kind_mark(screen, BASS_VOICE) == sample
            assert kind_mark(screen, PAD) == instrument
            assert voice_color(screen, FIRST_ROW, ChannelName.PULSE1) == sample
            assert voice_color(screen, PAD_ROW, ChannelName.PULSE2) == instrument
            assert voice_color(screen, EMPTY_ROW, ChannelName.PULSE1) == neutral
            assert voice_color(screen, CUT_ROW, ChannelName.PULSE1) == neutral
            assert is_dimmed(voice_color(screen, BASS_ROW, ChannelName.TRIANGLE), sample)

        def every_palette_paints_the_kinds(screen: Screen) -> None:
            painted_in(screen, catalog.get(DEFAULT_PALETTE_NAME))
            settings.open()
            screen.expect(settings.is_shown, bool, description="Display settings")

            for name in catalog.names:
                settings.choose_palette(name)
                screen.frames(SETTLING_FRAMES)

                painted_in(screen, catalog.get(name))

            settings.choose_palette(DEFAULT_PALETTE_NAME)
            settings.cancel()
            screen.expect(settings.is_shown, operator.not_, description="Display settings closed")

        screen.scenario(
            cut_a_cell_and_mute_the_triangle,
            every_palette_paints_the_kinds,
            leave_letting_the_project_go,
        ).run()


class TestColorsFollowTheVoice:
    """A voice's color travels with it: a placement's history line names it in its color, a move re-numbers and re-colors its cells and leaves the others alone, and the lines naming it keep its color once it is removed.

    An instrument is placed, moved up one place and removed after a confirmation.
    """

    def test_placed_moved_and_removed(self, screen: Screen) -> None:
        """Each step shows the instrument's number and color in the cells and in the history."""
        tracker = screen.sequencer.tracker
        voices = screen.sequencer.voices
        history = screen.sequencer.history
        palette = shipped_palettes().get(DEFAULT_PALETTE_NAME)
        sample = token_color(palette, SAMPLE_TOKEN)
        instrument = token_color(palette, INSTRUMENT_TOKEN)
        placed: List[Tuple[HistoryLine, int]] = []

        def place_the_instrument(screen: Screen) -> None:
            screen.tabs.bring_to_front(Tab.SEQUENCER)
            before = len(history.lines())

            type_into(screen, PLACED_ROW, ChannelName.PULSE1, PAD_NUMBER)

            lines = screen.expect(history.lines, lambda found: len(found) == before + 1, description="its entry")
            assert position_color(lines[0], PAD_NUMBER) == instrument
            assert voice_color(screen, PLACED_ROW, ChannelName.PULSE1) == instrument
            placed.append((lines[0], before + 1))

        def moving_it_up_renumbers_its_cells_alone(screen: Screen) -> None:
            row = screen.expect_item(partial(voices.row, PAD), description="the instrument's row")
            voices.pick(row)

            screen.press_shortcut(ShortcutId.VOICES_MOVE_VOICE_UP)

            screen.expect(voices.names, [LINE, PAD, BASS_VOICE].__eq__, description="the instrument moved up")
            screen.expect(
                partial(tracker.label, PAD_ROW, ChannelName.PULSE2, SubColumn.VOICE),
                FIRST_NUMBER.__eq__,
                description="its cell renumbered",
            )
            for row_index, channel, number, color in (
                (PAD_ROW, ChannelName.PULSE2, FIRST_NUMBER, instrument),
                (PLACED_ROW, ChannelName.PULSE1, FIRST_NUMBER, instrument),
                (BASS_ROW, ChannelName.TRIANGLE, PAD_NUMBER, sample),
                (FIRST_ROW, ChannelName.PULSE1, LINE_NUMBER, sample),
            ):
                assert tracker.label(row_index, channel, SubColumn.VOICE) == number
                assert voice_color(screen, row_index, channel) == color

        def removed_its_older_lines_keep_its_color(screen: Screen) -> None:
            prompt = voices.remove_prompt
            row = screen.expect_item(partial(voices.row, PAD), description="the instrument's row")
            voices.pick(row)
            screen.press_shortcut(ShortcutId.VOICES_REMOVE_VOICE)
            screen.expect(prompt.is_shown, bool, description="the question about removing")

            prompt.confirm()

            screen.expect(voices.names, [LINE, BASS_VOICE].__eq__, description="the instrument removed")
            line, count = placed[0]
            lines = history.lines()
            older = lines[len(lines) - count]
            assert older.segments == line.segments
            assert position_color(older, PAD_NUMBER) == instrument
            forgive_the_hover_race(screen)

        screen.scenario(
            place_the_instrument,
            moving_it_up_renumbers_its_cells_alone,
            removed_its_older_lines_keep_its_color,
            leave_letting_the_project_go,
        ).run()
