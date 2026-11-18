from dataclasses import dataclass
from itertools import cycle, islice
from string import ascii_letters
from typing import Callable, Final, List, Sequence, Set, Tuple

import pytest

from sampletones_player.specification.screen import (
    SCREEN_COLUMNS,
    SCREEN_WIDTH,
    SPRITE_BYTES,
    SPRITE_COUNT,
    SPRITE_SCANLINE_DELAY,
    TILE_SIDE,
)
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.groups import (
    BAR_GROUP,
    OTHER_METER_GROUP,
    PROGRESS_GROUP,
    PULSE_METER_GROUP,
    TileName,
)
from sampletones_tools.player.graphics.deck.markers import (
    MARKER_SLOTS,
    PIN_STEM_COLUMN,
    PIXELS_PER_PITCH,
    PULSE1_PIN,
    PULSE2_PIN,
    TRIANGLE_PIN,
    Pin,
)
from sampletones_tools.player.graphics.deck.meters import meter_members, progress_members
from sampletones_tools.player.graphics.deck.state import (
    DUTY_COUNT,
    LAST_PITCH,
    MAX_LEVEL,
    NOISE_PERIOD_COUNT,
    DeckState,
    NoiseState,
    PulseState,
    Transport,
    TriangleState,
)
from sampletones_tools.player.graphics.deck.texts import (
    REST_NOTE,
    UNKNOWN_CHARACTER,
    clock_text,
    noise_name,
    pitch_name,
)
from sampletones_tools.player.graphics.deck.waves import (
    NOISE_WAVES,
    OTHER_REST,
    PULSE_REST,
    PULSE_WAVES,
    TRIANGLE_WAVE,
    WAVE_PERIODS,
    Wave,
)
from sampletones_tools.player.graphics.layout.fields import ChannelFields, ProgramFields, TextField
from sampletones_tools.player.graphics.layout.screen import TEXT_GROUP, ScreenLayout
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.player.graphics.song_cells import (
    CLOCK_CELLS,
    METER_CELLS,
    NOTE_CELLS,
    ONE_CELL,
    WAVE_CELLS,
    WAVE_ROWS,
    CellPosition,
    action_safe,
    cells_of,
    progress_bar,
    title_safe,
)
from tests.unit.sampletones_tools.player.graphics.sprites import Sprite, shown_sprites, sprites_of

DUTY: Final[int] = 1
LEVEL: Final[int] = 9
PERIOD: Final[int] = 6
LOWEST_PITCH: Final[int] = 0
FIRST_PULSE_PITCH: Final[int] = 49
SECOND_PULSE_PITCH: Final[int] = 37
TRIANGLE_PITCH: Final[int] = 13
SHORT_LINE: Final[str] = "Amen Break"
UNDRAWN_LINE: Final[str] = "Café ☃"
UNDRAWN_LINE_SHOWN: Final[str] = "Caf" + UNKNOWN_CHARACTER + " " + UNKNOWN_CHARACTER
EXCESS: Final[int] = 5

SILENT_PULSE: Final[PulseState] = PulseState(duty=0, level=0, pitch=0)
RESTING_TRIANGLE: Final[TriangleState] = TriangleState(sounding=False, pitch=0)
SILENT_NOISE: Final[NoiseState] = NoiseState(level=0, period=0, short=False)
QUIET: Final[DeckState] = DeckState(
    title="",
    artist="",
    copyright="",
    pulse1=SILENT_PULSE,
    pulse2=SILENT_PULSE,
    triangle=RESTING_TRIANGLE,
    noise=SILENT_NOISE,
    played_seconds=0,
    total_seconds=0,
    progress=0,
    transport=Transport.STOPPED,
    shimmer=False,
)
FIRST_PULSE_SOUNDING: Final[DeckState] = QUIET.model_copy(
    update={"pulse1": PulseState(duty=DUTY, level=LEVEL, pitch=FIRST_PULSE_PITCH)}
)
SECOND_PULSE_SOUNDING: Final[DeckState] = QUIET.model_copy(
    update={"pulse2": PulseState(duty=DUTY, level=LEVEL, pitch=SECOND_PULSE_PITCH)}
)
TRIANGLE_SOUNDING: Final[DeckState] = QUIET.model_copy(
    update={"triangle": TriangleState(sounding=True, pitch=TRIANGLE_PITCH)}
)
ALL_SOUNDING: Final[DeckState] = QUIET.model_copy(
    update={
        "pulse1": PulseState(duty=DUTY, level=LEVEL, pitch=FIRST_PULSE_PITCH),
        "pulse2": PulseState(duty=DUTY, level=LEVEL, pitch=SECOND_PULSE_PITCH),
        "triangle": TriangleState(sounding=True, pitch=TRIANGLE_PITCH),
        "noise": NoiseState(level=LEVEL, period=PERIOD, short=False),
    }
)


def spelled(length: int) -> str:
    """A line of ``length`` letters, each one the font draws."""
    return "".join(islice(cycle(ascii_letters), length))


def noisy(*, short: bool, shimmer: bool) -> DeckState:
    return QUIET.model_copy(update={"noise": NoiseState(level=LEVEL, period=PERIOD, short=short), "shimmer": shimmer})


def cells_at(picture: Picture, row: int, column: int, width: int) -> bytes:
    start = row * SCREEN_COLUMNS + column
    return picture.nametable[start : start + width]


def tiles_of(sheet: TileSheet, group: str, members: Sequence[str]) -> bytes:
    return bytes(sheet.tile(PatternTable.BACKGROUND, group, member) for member in members)


def named_tiles(sheet: TileSheet, names: Sequence[TileName]) -> bytes:
    return bytes(sheet.tile(PatternTable.BACKGROUND, name.group, name.member) for name in names)


def wave_rows(sheet: TileSheet, wave: Wave) -> Tuple[bytes, bytes]:
    """The two rows of cells a wave shape fills, its period repeated along each."""
    return named_tiles(sheet, wave.top) * WAVE_PERIODS, named_tiles(sheet, wave.bottom) * WAVE_PERIODS


def wave_shown(picture: Picture, layout: ScreenLayout, row: int) -> Tuple[bytes, bytes]:
    column = layout.channels.wave_column
    return cells_at(picture, row, column, WAVE_CELLS), cells_at(picture, row + 1, column, WAVE_CELLS)


def markers_of(picture: Picture) -> List[Sprite]:
    """The keyboard markers a picture shows, held in the slots before the labels."""
    return shown_sprites(picture.sprites[: MARKER_SLOTS * SPRITE_BYTES])


def labels_of(picture: Picture) -> List[Sprite]:
    """The sprites from the slot after the markers on, the labels among them."""
    return sprites_of(picture.sprites)[MARKER_SLOTS:]


def label_sprites(layout: ScreenLayout, sheet: TileSheet) -> List[Sprite]:
    """The sprites the layout's labels state, one per character, top to bottom and left to right."""
    return [
        Sprite(
            vertical=label.row * TILE_SIDE - SPRITE_SCANLINE_DELAY,
            tile=sheet.tile(PatternTable.SPRITES, label.group, character),
            attributes=label.palette,
            horizontal=(label.column + offset) * TILE_SIDE,
        )
        for label in layout.labels
        for offset, character in enumerate(label.text)
    ]


def changed_cells(first: Picture, second: Picture) -> Set[CellPosition]:
    """The cells two pictures show another tile at."""
    return {
        divmod(index, SCREEN_COLUMNS)
        for index, (before, after) in enumerate(zip(first.nametable, second.nametable))
        if before != after
    }


@dataclass(frozen=True, kw_only=True)
class LevelCase(BaseRegularTestCase):
    level: int


LEVEL_CASES: Final[Tuple[LevelCase, ...]] = tuple(
    LevelCase(level=level, label=f"level {level}") for level in range(MAX_LEVEL + 1)
)


class TestTheRestingScreen(BaseTestSuite):
    def test_every_marker_is_hidden(self, shipped_deck: Deck) -> None:
        assert not markers_of(shipped_deck.resting())

    def test_the_sprite_memory_holds_every_sprite_of_the_console(self, shipped_deck: Deck) -> None:
        assert len(sprites_of(shipped_deck.resting().sprites)) == SPRITE_COUNT

    def test_it_carries_the_nametable_of_the_layout(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        assert shipped_deck.resting().nametable == shipped_layout.nametable(shipped_sheet)

    def test_it_carries_the_attribute_table_of_the_layout(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        assert shipped_deck.resting().attributes == shipped_layout.attribute_table()

    def test_it_carries_the_palette_of_the_layout(self, shipped_deck: Deck, shipped_layout: ScreenLayout) -> None:
        assert shipped_deck.resting().palette == shipped_layout.palettes.to_bytes()

    def test_the_shipped_deck_is_stated_over_the_shipped_layout_and_sheet(self, shipped_deck: Deck) -> None:
        assert Deck.load().resting() == shipped_deck.resting()


class TestTheLabels(BaseTestSuite):
    def test_each_character_stands_over_its_cell_in_the_palette_of_its_label(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        expected = label_sprites(shipped_layout, shipped_sheet)

        assert labels_of(shipped_deck.resting())[: len(expected)] == expected

    def test_every_sprite_after_the_labels_is_hidden(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        stated = len(label_sprites(shipped_layout, shipped_sheet))

        assert not [sprite for sprite in labels_of(shipped_deck.resting())[stated:] if sprite.shown]

    def test_the_labels_stand_still_while_a_song_plays(self, shipped_deck: Deck) -> None:
        assert labels_of(shipped_deck.showing(ALL_SOUNDING)) == labels_of(shipped_deck.resting())


class TestTheProgramLines(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        line: str
        field: Callable[[ProgramFields], TextField]

    test_cases = (
        TestCase(line="title", field=lambda program: program.title, label="the title"),
        TestCase(line="artist", field=lambda program: program.artist, label="the artist"),
        TestCase(line="copyright", field=lambda program: program.copyright, label="the copyright line"),
    )

    @staticmethod
    def shown(deck: Deck, layout: ScreenLayout, test_case: TestCase, text: str) -> bytes:
        picture = deck.showing(QUIET.model_copy(update={test_case.line: text}))
        field = test_case.field(layout.program)
        return cells_at(picture, field.row, field.column, field.width)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_short_line_is_padded_to_the_width_of_its_field(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        shown = self.shown(shipped_deck, shipped_layout, test_case, SHORT_LINE)

        expected = SHORT_LINE.ljust(test_case.field(shipped_layout.program).width)
        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, expected)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_character_the_font_leaves_out_is_shown_as_the_unknown_one(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        shown = self.shown(shipped_deck, shipped_layout, test_case, UNDRAWN_LINE)

        expected = UNDRAWN_LINE_SHOWN.ljust(test_case.field(shipped_layout.program).width)
        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, expected)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_long_line_is_cut_at_the_width_of_its_field(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        width = test_case.field(shipped_layout.program).width
        line = spelled(width + EXCESS)

        shown = self.shown(shipped_deck, shipped_layout, test_case, line)

        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, line[:width])

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_long_line_leaves_the_cells_around_its_field_as_they_were(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        field = test_case.field(shipped_layout.program)
        line = spelled(field.width + EXCESS)

        written = shipped_deck.showing(QUIET.model_copy(update={test_case.line: line}))

        cells = {(field.row, field.column + offset) for offset in range(field.width)}
        assert changed_cells(shipped_deck.showing(QUIET), written) == cells


class TestAChannelAtRest(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        state: DeckState
        row: Callable[[ChannelFields], int]
        wave: Wave
        meter_group: str

    test_cases = (
        TestCase(
            state=QUIET.model_copy(update={"pulse1": PulseState(duty=DUTY, level=0, pitch=FIRST_PULSE_PITCH)}),
            row=lambda channels: channels.pulse1_row,
            wave=PULSE_REST,
            meter_group=PULSE_METER_GROUP,
            label="a silent first pulse",
        ),
        TestCase(
            state=QUIET.model_copy(update={"pulse2": PulseState(duty=DUTY, level=0, pitch=SECOND_PULSE_PITCH)}),
            row=lambda channels: channels.pulse2_row,
            wave=PULSE_REST,
            meter_group=PULSE_METER_GROUP,
            label="a silent second pulse",
        ),
        TestCase(
            state=QUIET.model_copy(update={"triangle": TriangleState(sounding=False, pitch=TRIANGLE_PITCH)}),
            row=lambda channels: channels.triangle_row,
            wave=OTHER_REST,
            meter_group=OTHER_METER_GROUP,
            label="a resting triangle",
        ),
        TestCase(
            state=QUIET.model_copy(update={"noise": NoiseState(level=0, period=PERIOD, short=True)}),
            row=lambda channels: channels.noise_row,
            wave=OTHER_REST,
            meter_group=OTHER_METER_GROUP,
            label="a silent noise",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_note_reads_as_a_rest(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels

        picture = shipped_deck.showing(test_case.state)

        shown = cells_at(picture, test_case.row(channels), channels.note_column, NOTE_CELLS)
        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, REST_NOTE)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_no_marker_stands_over_the_keyboard(self, test_case: TestCase, shipped_deck: Deck) -> None:
        assert not markers_of(shipped_deck.showing(test_case.state))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_wave_lies_in_its_rest_shape(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        picture = shipped_deck.showing(test_case.state)

        shown = wave_shown(picture, shipped_layout, test_case.row(shipped_layout.channels))
        assert shown == wave_rows(shipped_sheet, test_case.wave)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_meter_lights_no_step(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels

        picture = shipped_deck.showing(test_case.state)

        shown = cells_at(picture, test_case.row(channels), channels.meter_column, METER_CELLS)
        assert shown == tiles_of(shipped_sheet, test_case.meter_group, meter_members(0))


class TestASoundingToneChannel(BaseTestSuite):
    """The console's sprite format is the contract the marker is read by.

    A sprite is four bytes of the sprite memory, its vertical position, tile, attributes and
    horizontal position, and it shows one scanline below the position it states.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        state: DeckState
        row: Callable[[ChannelFields], int]
        pin: Pin
        pitch: int

    test_cases = (
        TestCase(
            state=FIRST_PULSE_SOUNDING,
            row=lambda channels: channels.pulse1_row,
            pin=PULSE1_PIN,
            pitch=FIRST_PULSE_PITCH,
            label="the first pulse",
        ),
        TestCase(
            state=SECOND_PULSE_SOUNDING,
            row=lambda channels: channels.pulse2_row,
            pin=PULSE2_PIN,
            pitch=SECOND_PULSE_PITCH,
            label="the second pulse",
        ),
        TestCase(
            state=TRIANGLE_SOUNDING,
            row=lambda channels: channels.triangle_row,
            pin=TRIANGLE_PIN,
            pitch=TRIANGLE_PITCH,
            label="the triangle",
        ),
        TestCase(
            state=QUIET.model_copy(update={"pulse1": PulseState(duty=DUTY, level=LEVEL, pitch=LOWEST_PITCH)}),
            row=lambda channels: channels.pulse1_row,
            pin=PULSE1_PIN,
            pitch=LOWEST_PITCH,
            label="the first pulse on the lowest pitch",
        ),
        TestCase(
            state=QUIET.model_copy(update={"triangle": TriangleState(sounding=True, pitch=LAST_PITCH)}),
            row=lambda channels: channels.triangle_row,
            pin=TRIANGLE_PIN,
            pitch=LAST_PITCH,
            label="the triangle on the highest pitch",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_note_names_the_pitch(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels

        picture = shipped_deck.showing(test_case.state)

        shown = cells_at(picture, test_case.row(channels), channels.note_column, NOTE_CELLS)
        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, pitch_name(test_case.pitch))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_one_marker_stands_over_the_pitch(self, test_case: TestCase, shipped_deck: Deck) -> None:
        markers = markers_of(shipped_deck.showing(test_case.state))

        assert [marker.horizontal for marker in markers] == [shipped_deck.marker_x(test_case.pitch)]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_marker_stands_in_the_lane_row(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        """The marker states the scanline above the lane, so its top row is shown on the lane's first."""
        markers = markers_of(shipped_deck.showing(test_case.state))

        assert [marker.top for marker in markers] == [shipped_layout.keyboard.lane_row * TILE_SIDE]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_marker_is_the_pin_of_the_channel(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_sheet: TileSheet,
    ) -> None:
        markers = markers_of(shipped_deck.showing(test_case.state))

        tile = shipped_sheet.tile(PatternTable.SPRITES, test_case.pin.group, test_case.pin.member)
        assert [(marker.tile, marker.attributes) for marker in markers] == [(tile, test_case.pin.palette)]


class TestSeveralChannelsSounding(BaseTestSuite):
    def test_every_sounding_tone_channel_has_a_marker_over_its_pitch(self, shipped_deck: Deck) -> None:
        markers = markers_of(shipped_deck.showing(ALL_SOUNDING))

        pitches = (FIRST_PULSE_PITCH, SECOND_PULSE_PITCH, TRIANGLE_PITCH)
        assert sorted(marker.horizontal for marker in markers) == sorted(
            shipped_deck.marker_x(pitch) for pitch in pitches
        )

    def test_every_channel_shows_its_own_pin(self, shipped_deck: Deck, shipped_sheet: TileSheet) -> None:
        markers = markers_of(shipped_deck.showing(ALL_SOUNDING))

        expected = {
            (shipped_sheet.tile(PatternTable.SPRITES, pin.group, pin.member), pin.palette, shipped_deck.marker_x(pitch))
            for pin, pitch in (
                (PULSE1_PIN, FIRST_PULSE_PITCH),
                (PULSE2_PIN, SECOND_PULSE_PITCH),
                (TRIANGLE_PIN, TRIANGLE_PITCH),
            )
        }
        assert {(marker.tile, marker.attributes, marker.horizontal) for marker in markers} == expected

    def test_the_noise_adds_no_marker(self, shipped_deck: Deck) -> None:
        assert not markers_of(shipped_deck.showing(noisy(short=False, shimmer=False)))


class TestWhereAMarkerStands(BaseTestSuite):
    def test_a_pitch_higher_moves_the_marker_by_the_pixels_of_a_pitch(self, shipped_deck: Deck) -> None:
        steps = {shipped_deck.marker_x(pitch + 1) - shipped_deck.marker_x(pitch) for pitch in range(LAST_PITCH)}

        assert steps == {PIXELS_PER_PITCH}

    def test_the_stem_of_the_lowest_pitch_stands_on_the_first_pixel_of_the_keyboard(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        stem = shipped_deck.marker_x(LOWEST_PITCH) + PIN_STEM_COLUMN

        assert stem == shipped_layout.keyboard.column * TILE_SIDE

    def test_the_marker_of_every_pitch_lies_on_the_screen(self, shipped_deck: Deck) -> None:
        positions = [shipped_deck.marker_x(pitch) for pitch in range(LAST_PITCH + 1)]

        assert min(positions) >= 0
        assert max(positions) + TILE_SIDE <= SCREEN_WIDTH


class TestTheShapeOfAPulse(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        duty: int

    test_cases = (
        TestCase(duty=0, label="the narrowest duty"),
        TestCase(duty=1, label="the second duty"),
        TestCase(duty=2, label="the third duty"),
        TestCase(duty=DUTY_COUNT - 1, label="the widest duty"),
    )

    @staticmethod
    def shown(deck: Deck, layout: ScreenLayout, duty: int) -> Tuple[bytes, bytes]:
        state = QUIET.model_copy(update={"pulse1": PulseState(duty=duty, level=LEVEL, pitch=FIRST_PULSE_PITCH)})
        return wave_shown(deck.showing(state), layout, layout.channels.pulse1_row)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_duty_draws_its_shape_over_both_periods(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        shown = self.shown(shipped_deck, shipped_layout, test_case.duty)

        assert shown == wave_rows(shipped_sheet, PULSE_WAVES[test_case.duty])

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_shape_repeats_along_each_row(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        period = WAVE_CELLS // WAVE_PERIODS

        for row in self.shown(shipped_deck, shipped_layout, test_case.duty):
            assert row == row[:period] * WAVE_PERIODS

    def test_every_duty_draws_a_shape_of_its_own(self, shipped_deck: Deck, shipped_layout: ScreenLayout) -> None:
        shapes = {self.shown(shipped_deck, shipped_layout, duty) for duty in range(DUTY_COUNT)}

        assert len(shapes) == DUTY_COUNT


class TestTheLevelMeters(BaseTestSuite):
    test_cases = LEVEL_CASES

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_pulse_lights_the_steps_of_its_level(
        self,
        test_case: LevelCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels
        pulse = PulseState(duty=DUTY, level=test_case.level, pitch=SECOND_PULSE_PITCH)

        picture = shipped_deck.showing(QUIET.model_copy(update={"pulse2": pulse}))

        shown = cells_at(picture, channels.pulse2_row, channels.meter_column, METER_CELLS)
        assert shown == tiles_of(shipped_sheet, PULSE_METER_GROUP, meter_members(test_case.level))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_noise_lights_the_steps_of_its_level(
        self,
        test_case: LevelCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels
        noise = NoiseState(level=test_case.level, period=PERIOD, short=False)

        picture = shipped_deck.showing(QUIET.model_copy(update={"noise": noise}))

        shown = cells_at(picture, channels.noise_row, channels.meter_column, METER_CELLS)
        assert shown == tiles_of(shipped_sheet, OTHER_METER_GROUP, meter_members(test_case.level))

    def test_a_sounding_triangle_lights_its_whole_meter(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels

        picture = shipped_deck.showing(TRIANGLE_SOUNDING)

        shown = cells_at(picture, channels.triangle_row, channels.meter_column, METER_CELLS)
        assert shown == tiles_of(shipped_sheet, OTHER_METER_GROUP, meter_members(MAX_LEVEL))


class TestTheNoteOfTheNoise(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        period: int

    test_cases = (
        TestCase(period=0, label="the first period"),
        TestCase(period=PERIOD, label="a period in the middle"),
        TestCase(period=NOISE_PERIOD_COUNT - 1, label="the last period"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_sounding_noise_names_its_period(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        channels = shipped_layout.channels
        noise = NoiseState(level=LEVEL, period=test_case.period, short=False)

        picture = shipped_deck.showing(QUIET.model_copy(update={"noise": noise}))

        shown = cells_at(picture, channels.noise_row, channels.note_column, NOTE_CELLS)
        assert shown == tiles_of(shipped_sheet, TEXT_GROUP, noise_name(test_case.period))


class TestTheShimmerOfTheNoise(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        short: bool

    test_cases = (
        TestCase(short=False, label="the long sequence"),
        TestCase(short=True, label="the short sequence"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_two_arrangements_differ_in_the_wave_cells_and_nowhere_else(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        channels = shipped_layout.channels
        still = shipped_deck.showing(noisy(short=test_case.short, shimmer=False))
        moved = shipped_deck.showing(noisy(short=test_case.short, shimmer=True))

        changed = changed_cells(still, moved)

        wave = {
            (channels.noise_row + row, channels.wave_column + cell)
            for row in range(WAVE_ROWS)
            for cell in range(WAVE_CELLS)
        }
        assert changed
        assert changed <= wave
        assert (still.attributes, still.palette, still.sprites) == (moved.attributes, moved.palette, moved.sprites)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_arrangement_draws_the_shape_the_sequence_states(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        for shimmer in (False, True):
            picture = shipped_deck.showing(noisy(short=test_case.short, shimmer=shimmer))

            shown = wave_shown(picture, shipped_layout, shipped_layout.channels.noise_row)
            assert shown == wave_rows(shipped_sheet, NOISE_WAVES[test_case.short][int(shimmer)])

    def test_the_short_sequence_draws_another_shape_than_the_long_one(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        row = shipped_layout.channels.noise_row
        long = wave_shown(shipped_deck.showing(noisy(short=False, shimmer=False)), shipped_layout, row)
        short = wave_shown(shipped_deck.showing(noisy(short=True, shimmer=False)), shipped_layout, row)

        assert long != short

    def test_a_silent_noise_stands_still(self, shipped_deck: Deck) -> None:
        still = shipped_deck.showing(QUIET)
        moved = shipped_deck.showing(QUIET.model_copy(update={"shimmer": True}))

        assert still == moved


class TestTheTimes(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        played: int
        total: int

    test_cases = (
        TestCase(played=0, total=0, label="a song of no length"),
        TestCase(played=0, total=225, label="a song about to start"),
        TestCase(played=83, total=225, label="a song in full flow"),
        TestCase(played=3599, total=3599, label="an hour gone by"),
    )

    @staticmethod
    def showing(deck: Deck, test_case: TestCase) -> Picture:
        return deck.showing(
            QUIET.model_copy(update={"played_seconds": test_case.played, "total_seconds": test_case.total})
        )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_time_played_lands_at_its_field(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        transport = shipped_layout.transport

        picture = self.showing(shipped_deck, test_case)

        shown = cells_at(picture, transport.row, transport.played_column, CLOCK_CELLS)
        assert shown == tiles_of(shipped_sheet, BAR_GROUP, clock_text(test_case.played))

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_whole_length_lands_at_its_field(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        transport = shipped_layout.transport

        picture = self.showing(shipped_deck, test_case)

        shown = cells_at(picture, transport.row, transport.total_column, CLOCK_CELLS)
        assert shown == tiles_of(shipped_sheet, BAR_GROUP, clock_text(test_case.total))


class TestThePlayingState(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        transport: Transport

    test_cases = (
        TestCase(transport=Transport.PLAYING, label="playing"),
        TestCase(transport=Transport.PAUSED, label="paused"),
        TestCase(transport=Transport.STOPPED, label="stopped"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_its_glyph_lands_at_its_field(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        transport = shipped_layout.transport

        picture = shipped_deck.showing(QUIET.model_copy(update={"transport": test_case.transport}))

        shown = cells_at(picture, transport.row, transport.state_column, ONE_CELL)
        assert shown == tiles_of(shipped_sheet, BAR_GROUP, [test_case.transport.value])


class TestTheProgressBar(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        filled: Callable[[int], int]

    test_cases = (
        TestCase(filled=lambda pixels: 0, label="an empty bar"),
        TestCase(filled=lambda pixels: 1, label="one pixel"),
        TestCase(filled=lambda pixels: pixels // 2, label="half the song"),
        TestCase(filled=lambda pixels: pixels, label="the whole song"),
        TestCase(filled=lambda pixels: pixels + TILE_SIDE, label="more than the bar holds"),
    )

    @staticmethod
    def shown(deck: Deck, layout: ScreenLayout, filled: int) -> bytes:
        progress = layout.progress
        picture = deck.showing(QUIET.model_copy(update={"progress": filled}))
        return cells_at(picture, progress.row, progress.column, progress.width)

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bar_shows_the_tiles_of_its_progress(
        self,
        test_case: TestCase,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        width = shipped_layout.progress.width
        filled = test_case.filled(width * TILE_SIDE)

        shown = self.shown(shipped_deck, shipped_layout, filled)

        assert shown == tiles_of(shipped_sheet, PROGRESS_GROUP, progress_members(filled, width))

    def test_a_full_bar_differs_from_an_empty_one_in_every_cell(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        empty = self.shown(shipped_deck, shipped_layout, 0)
        full = self.shown(shipped_deck, shipped_layout, shipped_layout.progress.width * TILE_SIDE)

        assert all(before != after for before, after in zip(empty, full))

    def test_more_than_the_bar_holds_reads_as_a_full_bar(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        pixels = shipped_layout.progress.width * TILE_SIDE

        assert self.shown(shipped_deck, shipped_layout, pixels + TILE_SIDE) == self.shown(
            shipped_deck, shipped_layout, pixels
        )


class TestWhatASongLeavesAlone(BaseTestSuite):
    """Columns 2-29 and rows 3-26 are the television title-safe area of a 256x240 picture.

    The progress bar repeats what the clock states, so it may take the wider action-safe area,
    columns 1-30 and rows 1-28.
    """

    @staticmethod
    def busy(layout: ScreenLayout) -> DeckState:
        """A song in full flow whose every line overruns its field."""
        line = spelled(SCREEN_COLUMNS)
        return ALL_SOUNDING.model_copy(
            update={
                "title": line,
                "artist": line,
                "copyright": line,
                "played_seconds": 83,
                "total_seconds": 225,
                "progress": layout.progress.width * TILE_SIDE,
                "transport": Transport.PLAYING,
                "shimmer": True,
            }
        )

    def test_the_attribute_table_stays_the_one_the_layout_states(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        assert shipped_deck.showing(self.busy(shipped_layout)).attributes == shipped_layout.attribute_table()

    def test_the_palette_stays_the_one_the_layout_states(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        assert shipped_deck.showing(self.busy(shipped_layout)).palette == shipped_layout.palettes.to_bytes()

    def test_every_cell_a_song_changes_besides_the_progress_bar_lies_inside_the_title_safe_area(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        changed = changed_cells(shipped_deck.resting(), shipped_deck.showing(self.busy(shipped_layout)))
        readings = changed - set(cells_of(progress_bar(shipped_layout)))

        assert readings
        assert not [(row, column) for row, column in sorted(readings) if not title_safe(row, column)]

    def test_every_cell_a_song_changes_lies_inside_the_action_safe_area(
        self,
        shipped_deck: Deck,
        shipped_layout: ScreenLayout,
    ) -> None:
        changed = changed_cells(shipped_deck.resting(), shipped_deck.showing(self.busy(shipped_layout)))

        assert changed
        assert not [(row, column) for row, column in sorted(changed) if not action_safe(row, column)]
