from dataclasses import dataclass
from itertools import combinations
from typing import Callable, Final, List, Mapping, Sequence, Set, Tuple, Union

import pytest
from pydantic import ValidationError

from sampletones_player.specification.screen import (
    ATTRIBUTE_CELL_TILES,
    ATTRIBUTE_COLUMNS,
    ATTRIBUTE_ROWS,
    ATTRIBUTE_TABLE_SIZE,
    NAMETABLE_SIZE,
    PALETTES_PER_LAYER,
    SCREEN_COLUMNS,
    SCREEN_ROWS,
)
from sampletones_tools.player.graphics.layout.cells import LAST_COLUMN, LAST_ROW
from sampletones_tools.player.graphics.layout.elements import PatternElement, TextElement
from sampletones_tools.player.graphics.layout.fields import ChannelFields
from sampletones_tools.player.graphics.layout.screen import EMPTY_CELL, TEXT_GROUP, ScreenLayout
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.player.graphics.song_cells import (
    CLOCK_CELLS,
    ONE_CELL,
    ONE_ROW,
    WAVE_ROWS,
    CellPosition,
    Span,
    action_safe,
    cells_of,
    channel,
    keyboard_row,
    program_line,
    progress_bar,
    title_safe,
    transport_cells,
)

Square = Tuple[int, int]
AnyElement = Union[TextElement, PatternElement]

FIRST_PALETTE: Final[int] = 0
LAST_PALETTE: Final[int] = PALETTES_PER_LAYER - 1
PALETTE: Final[int] = 2
BYTES_PER_ROW: Final[int] = 8
ALL_FOUR_PALETTES: Final[int] = 0b11_10_01_00
FULL_BLOCK: Final[int] = 0xFF
UPPER_SQUARES: Final[int] = 0x0F

ROW: Final[int] = 9
COLUMN: Final[int] = 4
TEXT: Final[str] = "Tune"
OTHER_TEXT: Final[str] = "Song"
PAIR: Final[str] = "ab"
ABSENT_GROUP: Final[str] = "nowhere"

SHAPE_REFUSAL: Final[str] = "rows of"
DIGIT_REFUSAL: Final[str] = "background palettes"
EDGE_REFUSAL: Final[str] = "past the screen's edge"


@dataclass(frozen=True, kw_only=True)
class ChannelCase(BaseRegularTestCase):
    row: Callable[[ChannelFields], int]


CHANNEL_CASES: Final[Tuple[ChannelCase, ...]] = (
    ChannelCase(row=lambda channels: channels.pulse1_row, label="the first pulse"),
    ChannelCase(row=lambda channels: channels.pulse2_row, label="the second pulse"),
    ChannelCase(row=lambda channels: channels.triangle_row, label="the triangle"),
    ChannelCase(row=lambda channels: channels.noise_row, label="the noise"),
)


def grid(squares: Mapping[Square, int]) -> Tuple[str, ...]:
    """An attribute grid of the first palette with the stated squares recolored."""
    return tuple(
        "".join(str(squares.get((row, column), FIRST_PALETTE)) for column in range(ATTRIBUTE_COLUMNS))
        for row in range(ATTRIBUTE_ROWS)
    )


BLANK: Final[Tuple[str, ...]] = grid({})


def recolored(layout: ScreenLayout, attributes: Sequence[str]) -> ScreenLayout:
    """The layout read anew with another attribute grid, so the grid passes the model's checks."""
    return ScreenLayout.model_validate({**layout.model_dump(), "attributes": tuple(attributes)})


def showing(layout: ScreenLayout, elements: Sequence[AnyElement]) -> ScreenLayout:
    """The layout with other fixed elements than the shipped ones."""
    return layout.model_copy(update={"elements": tuple(elements)})


def text_at(row: int, column: int, text: str) -> TextElement:
    return TextElement(kind="text", row=row, column=column, group=TEXT_GROUP, text=text)


def block_at(row: int, column: int, *, width: int, height: int) -> PatternElement:
    return PatternElement(
        kind="pattern",
        row=row,
        column=column,
        width=width,
        height=height,
        group=TEXT_GROUP,
        members=tuple(PAIR),
    )


def text_tiles(sheet: TileSheet, text: str) -> bytes:
    return bytes(sheet.tile(PatternTable.BACKGROUND, TEXT_GROUP, character) for character in text)


class TestTheNametable(BaseTestSuite):
    def test_the_shipped_screen_fills_every_cell(self, shipped_layout: ScreenLayout, shipped_sheet: TileSheet) -> None:
        assert len(shipped_layout.nametable(shipped_sheet)) == NAMETABLE_SIZE

    def test_a_cell_no_element_takes_shows_the_empty_text_tile(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        nametable = showing(shipped_layout, []).nametable(shipped_sheet)

        assert nametable == text_tiles(shipped_sheet, EMPTY_CELL) * NAMETABLE_SIZE

    def test_an_element_is_written_at_its_cells_row_by_row(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        nametable = showing(shipped_layout, [text_at(ROW, COLUMN, TEXT)]).nametable(shipped_sheet)

        expected = bytearray(text_tiles(shipped_sheet, EMPTY_CELL) * NAMETABLE_SIZE)
        start = ROW * SCREEN_COLUMNS + COLUMN
        expected[start : start + len(TEXT)] = text_tiles(shipped_sheet, TEXT)
        assert nametable == bytes(expected)

    def test_a_later_element_is_drawn_over_an_earlier_one(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        elements = [text_at(ROW, COLUMN, TEXT), text_at(ROW, COLUMN, OTHER_TEXT)]

        nametable = showing(shipped_layout, elements).nametable(shipped_sheet)

        start = ROW * SCREEN_COLUMNS + COLUMN
        assert nametable[start : start + len(OTHER_TEXT)] == text_tiles(shipped_sheet, OTHER_TEXT)

    def test_an_element_ending_at_the_last_cell_is_drawn(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        element = text_at(LAST_ROW, SCREEN_COLUMNS - len(TEXT), TEXT)

        nametable = showing(shipped_layout, [element]).nametable(shipped_sheet)

        assert nametable[-len(TEXT) :] == text_tiles(shipped_sheet, TEXT)

    def test_an_element_of_a_group_the_sheet_lacks_is_a_key_error(
        self,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        element = text_at(ROW, COLUMN, TEXT).model_copy(update={"group": ABSENT_GROUP})

        with pytest.raises(KeyError):
            showing(shipped_layout, [element]).nametable(shipped_sheet)


class TestAnElementReachingPastTheEdge(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        element: AnyElement

    test_cases = (
        TestCase(element=text_at(ROW, LAST_COLUMN, PAIR), label="a text running off the right edge"),
        TestCase(
            element=text_at(LAST_ROW, SCREEN_COLUMNS - len(TEXT) + 1, TEXT),
            label="a text running off the last cell",
        ),
        TestCase(
            element=block_at(ROW, LAST_COLUMN, width=len(PAIR), height=ONE_ROW),
            label="a block wider than the room beside it",
        ),
        TestCase(
            element=block_at(LAST_ROW, COLUMN, width=ONE_CELL, height=WAVE_ROWS),
            label="a block taller than the room below it",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_nametable_is_refused(
        self,
        test_case: TestCase,
        shipped_layout: ScreenLayout,
        shipped_sheet: TileSheet,
    ) -> None:
        with pytest.raises(ValueError, match=EDGE_REFUSAL):
            showing(shipped_layout, [test_case.element]).nametable(shipped_sheet)


class TestTheAttributeMemory(BaseTestSuite):
    """The console's attribute format is the contract, so the cases spell its bytes out.

    A byte colors a block of four squares, each two cells wide and two tall, in two bits a
    square: the top left square in the low bits, then the top right, the bottom left and the
    bottom right. Eight bytes cover a row of blocks.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        square: Square
        byte: int
        shift: int

    test_cases = (
        TestCase(square=(0, 0), byte=0, shift=0, label="the top left square of the first byte"),
        TestCase(square=(0, 1), byte=0, shift=2, label="the top right square"),
        TestCase(square=(1, 0), byte=0, shift=4, label="the bottom left square"),
        TestCase(square=(1, 1), byte=0, shift=6, label="the bottom right square"),
        TestCase(square=(0, 2), byte=1, shift=0, label="the next byte along the row"),
        TestCase(square=(2, 0), byte=8, shift=0, label="the next row of bytes"),
        TestCase(square=(5, 9), byte=20, shift=6, label="a square in the middle of the screen"),
        TestCase(square=(14, 15), byte=63, shift=2, label="the last square of the screen"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_square_sets_its_own_two_bits_and_no_others(
        self,
        test_case: TestCase,
        shipped_layout: ScreenLayout,
    ) -> None:
        for palette in range(FIRST_PALETTE + 1, PALETTES_PER_LAYER):
            layout = recolored(shipped_layout, grid({test_case.square: palette}))

            expected = bytearray(ATTRIBUTE_TABLE_SIZE)
            expected[test_case.byte] = palette << test_case.shift
            assert layout.attribute_table() == bytes(expected)

    def test_four_squares_share_a_byte(self, shipped_layout: ScreenLayout) -> None:
        layout = recolored(shipped_layout, grid({(0, 0): 0, (0, 1): 1, (1, 0): 2, (1, 1): 3}))

        assert layout.attribute_table()[0] == ALL_FOUR_PALETTES

    def test_the_last_row_of_bytes_colors_the_upper_two_rows_of_cells_alone(
        self,
        shipped_layout: ScreenLayout,
    ) -> None:
        """The screen is thirty cells tall, so the last bytes leave the bits of their lower squares at zero."""
        layout = recolored(shipped_layout, (str(LAST_PALETTE) * ATTRIBUTE_COLUMNS,) * ATTRIBUTE_ROWS)

        table = layout.attribute_table()

        assert table[:-BYTES_PER_ROW] == bytes([FULL_BLOCK]) * (ATTRIBUTE_TABLE_SIZE - BYTES_PER_ROW)
        assert table[-BYTES_PER_ROW:] == bytes([UPPER_SQUARES]) * BYTES_PER_ROW

    def test_the_shipped_screen_fills_the_attribute_memory(self, shipped_layout: ScreenLayout) -> None:
        assert len(shipped_layout.attribute_table()) == ATTRIBUTE_TABLE_SIZE


class TestThePaletteOfACell(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        square: Square

    test_cases = (
        TestCase(square=(0, 0), label="the first square"),
        TestCase(square=(7, 3), label="a square in the middle of the screen"),
        TestCase(square=(ATTRIBUTE_ROWS - 1, ATTRIBUTE_COLUMNS - 1), label="the last square"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_square_colors_its_own_four_cells(self, test_case: TestCase, shipped_layout: ScreenLayout) -> None:
        layout = recolored(shipped_layout, grid({test_case.square: PALETTE}))

        colored = {
            (row, column)
            for row in range(SCREEN_ROWS)
            for column in range(SCREEN_COLUMNS)
            if layout.palette_at(row, column) == PALETTE
        }

        square_row, square_column = test_case.square
        assert colored == {
            (square_row * ATTRIBUTE_CELL_TILES + row, square_column * ATTRIBUTE_CELL_TILES + column)
            for row in range(ATTRIBUTE_CELL_TILES)
            for column in range(ATTRIBUTE_CELL_TILES)
        }

    def test_every_cell_of_the_shipped_screen_takes_a_background_palette(self, shipped_layout: ScreenLayout) -> None:
        palettes = {
            shipped_layout.palette_at(row, column) for row in range(SCREEN_ROWS) for column in range(SCREEN_COLUMNS)
        }

        assert palettes <= set(range(PALETTES_PER_LAYER))


class TestAnAttributeGridTheLayoutRefuses(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        attributes: Tuple[str, ...]
        expected: str

    test_cases = (
        TestCase(attributes=BLANK[:-1], expected=SHAPE_REFUSAL, label="a row short"),
        TestCase(attributes=(*BLANK, BLANK[0]), expected=SHAPE_REFUSAL, label="a row over"),
        TestCase(attributes=(), expected=SHAPE_REFUSAL, label="no rows at all"),
        TestCase(attributes=(BLANK[0][:-1], *BLANK[1:]), expected=SHAPE_REFUSAL, label="a row a digit short"),
        TestCase(
            attributes=(BLANK[0] + str(FIRST_PALETTE), *BLANK[1:]),
            expected=SHAPE_REFUSAL,
            label="a row a digit over",
        ),
        TestCase(
            attributes=grid({(0, 0): PALETTES_PER_LAYER}),
            expected=DIGIT_REFUSAL,
            label="a palette past the fourth",
        ),
        TestCase(
            attributes=("x" * ATTRIBUTE_COLUMNS, *BLANK[1:]),
            expected=DIGIT_REFUSAL,
            label="a row of letters",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_refusal_names_what_a_grid_holds(self, test_case: TestCase, shipped_layout: ScreenLayout) -> None:
        with pytest.raises(ValidationError, match=test_case.expected):
            recolored(shipped_layout, test_case.attributes)

    def test_a_grid_stated_as_a_block_of_text_reads_as_its_rows(self, shipped_layout: ScreenLayout) -> None:
        rows = grid({(3, 5): PALETTE})
        stated = {**shipped_layout.model_dump(), "attributes": "\n".join(rows) + "\n"}

        assert ScreenLayout.model_validate(stated) == recolored(shipped_layout, rows)

    def test_the_shipped_layout_reads_back_from_what_it_states(self, shipped_layout: ScreenLayout) -> None:
        assert ScreenLayout.model_validate(shipped_layout.model_dump()) == shipped_layout


class TestTheSongStaysInsideTheTitleSafeArea(BaseTestSuite):
    """Columns 2-29 and rows 3-26 are the television title-safe area of a 256x240 picture.

    A television may hide the edges of the picture, so whatever a song writes lies inside the
    area every set shows.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        spans: Callable[[ScreenLayout], List[Span]]

    test_cases = (
        TestCase(spans=lambda layout: program_line(layout.program.title), label="the title"),
        TestCase(spans=lambda layout: program_line(layout.program.artist), label="the artist"),
        TestCase(spans=lambda layout: program_line(layout.program.copyright), label="the copyright line"),
        TestCase(
            spans=lambda layout: transport_cells(layout, layout.transport.state_column, ONE_CELL),
            label="the playing state",
        ),
        TestCase(
            spans=lambda layout: transport_cells(layout, layout.transport.played_column, CLOCK_CELLS),
            label="the time played",
        ),
        TestCase(
            spans=lambda layout: transport_cells(layout, layout.transport.total_column, CLOCK_CELLS),
            label="the whole length",
        ),
        TestCase(spans=lambda layout: channel(layout, layout.channels.pulse1_row), label="the first pulse"),
        TestCase(spans=lambda layout: channel(layout, layout.channels.pulse2_row), label="the second pulse"),
        TestCase(spans=lambda layout: channel(layout, layout.channels.triangle_row), label="the triangle"),
        TestCase(spans=lambda layout: channel(layout, layout.channels.noise_row), label="the noise"),
        TestCase(spans=lambda layout: keyboard_row(layout, layout.keyboard.key_row), label="the keys"),
        TestCase(spans=lambda layout: keyboard_row(layout, layout.keyboard.lane_row), label="the marker lane"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_cell_of_the_field_lies_inside_the_area(
        self,
        test_case: TestCase,
        shipped_layout: ScreenLayout,
    ) -> None:
        cells = cells_of(test_case.spans(shipped_layout))

        assert cells
        assert not [(row, column) for row, column in cells if not title_safe(row, column)]


class TestTheProgressBarStaysInsideTheActionSafeArea(BaseTestSuite):
    """The bar repeats what the clock states, so it may take the wider area nearly every set shows."""

    def test_every_cell_of_the_bar_lies_inside_the_area(self, shipped_layout: ScreenLayout) -> None:
        cells = cells_of(progress_bar(shipped_layout))

        assert cells
        assert not [(row, column) for row, column in cells if not action_safe(row, column)]


class TestAChannelOwnsItsColorCells(BaseTestSuite):
    """A channel is recolored through the squares its two rows cover, so those squares are its own."""

    test_cases = CHANNEL_CASES

    @staticmethod
    def squares(cells: Sequence[CellPosition]) -> Set[Square]:
        return {(row // ATTRIBUTE_CELL_TILES, column // ATTRIBUTE_CELL_TILES) for row, column in cells}

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_every_cell_the_channel_writes_takes_the_same_palette(
        self,
        test_case: ChannelCase,
        shipped_layout: ScreenLayout,
    ) -> None:
        cells = cells_of(channel(shipped_layout, test_case.row(shipped_layout.channels)))

        palettes = {shipped_layout.palette_at(row, column) for row, column in cells}

        assert len(palettes) == 1

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_two_rows_of_the_channel_fill_one_row_of_squares(
        self,
        test_case: ChannelCase,
        shipped_layout: ScreenLayout,
    ) -> None:
        cells = cells_of(channel(shipped_layout, test_case.row(shipped_layout.channels)))

        assert len({row for row, _ in self.squares(cells)}) == 1

    def test_no_two_channels_write_into_one_square(self, shipped_layout: ScreenLayout) -> None:
        taken = [
            self.squares(cells_of(channel(shipped_layout, test_case.row(shipped_layout.channels))))
            for test_case in CHANNEL_CASES
        ]

        assert all(not first & second for first, second in combinations(taken, 2))
