from dataclasses import dataclass
from typing import Final, Tuple

import numpy as np
import pytest

from sampletones_player.specification.screen import (
    COLORS_PER_PALETTE,
    PATTERN_TABLE_SIZE,
    PATTERNS_SIZE,
    TILE_BYTES,
    TILE_SIDE,
    TILES_PER_TABLE,
)
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.patterns import (
    HIGH_PLANE_BIT,
    LOW_PLANE_BIT,
    plane_row,
    planes_tile,
    sheet_patterns,
    table_tiles,
    tile_planes,
)
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SEED: Final[int] = 11
PLANE_BYTES: Final[int] = TILE_SIDE
FULL_ROW: Final[int] = 0xFF
LEFTMOST_PIXEL: Final[int] = 0x80
RIGHTMOST_PIXEL: Final[int] = 0x01
THIRD_PIXEL: Final[int] = 0x20
LAST_ROW: Final[int] = TILE_SIDE - 1
LAST_COLUMN: Final[int] = TILE_SIDE - 1
LAST_TILE: Final[int] = TILES_PER_TABLE - 1
EMPTY: Final[Pixels] = ((0,) * TILE_SIDE,) * TILE_SIDE
MIXED_ROW: Final[Tuple[int, ...]] = (1, 2, 3, 0, 0, 3, 2, 1)
MIXED_LOW_PLANE: Final[int] = 0b10100101
MIXED_HIGH_PLANE: Final[int] = 0b01100110
SIZE_REFUSAL: Final[str] = "pattern tables take"


def uniform(color: int) -> Pixels:
    return ((color,) * TILE_SIDE,) * TILE_SIDE


def single(row: int, column: int, color: int) -> Pixels:
    """A tile empty but for one pixel."""
    return tuple(
        tuple(color if (at_row, at_column) == (row, column) else 0 for at_column in range(TILE_SIDE))
        for at_row in range(TILE_SIDE)
    )


def scattered(seed: int) -> Pixels:
    generator = np.random.default_rng(seed)
    entries = generator.integers(0, COLORS_PER_PALETTE, size=(TILE_SIDE, TILE_SIDE))
    return tuple(tuple(int(entry) for entry in row) for row in entries)


def stated(low: bytes, high: bytes) -> bytes:
    """A tile's sixteen bytes from the rows each plane states, a row left out standing empty."""
    return low.ljust(PLANE_BYTES, b"\x00") + high.ljust(PLANE_BYTES, b"\x00")


class TestTheBytesOfATile(BaseTestSuite):
    """The console's pattern format is the contract, so the cases spell its bytes out.

    A tile takes eight bytes of its low bit plane followed by eight of its high one, a byte per
    row from the top, the leftmost pixel in the top bit.
    """

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pixels: Pixels
        expected: bytes

    test_cases = (
        TestCase(pixels=EMPTY, expected=stated(b"", b""), label="an empty tile"),
        TestCase(
            pixels=uniform(1),
            expected=stated(bytes([FULL_ROW] * PLANE_BYTES), b""),
            label="entry one fills the low plane",
        ),
        TestCase(
            pixels=uniform(2),
            expected=stated(b"", bytes([FULL_ROW] * PLANE_BYTES)),
            label="entry two fills the high plane",
        ),
        TestCase(
            pixels=uniform(3),
            expected=stated(bytes([FULL_ROW] * PLANE_BYTES), bytes([FULL_ROW] * PLANE_BYTES)),
            label="entry three fills both planes",
        ),
        TestCase(
            pixels=single(0, 0, 1),
            expected=stated(bytes([LEFTMOST_PIXEL]), b""),
            label="the top left pixel is the top bit of the first byte",
        ),
        TestCase(
            pixels=single(0, LAST_COLUMN, 1),
            expected=stated(bytes([RIGHTMOST_PIXEL]), b""),
            label="the top right pixel is the low bit of the first byte",
        ),
        TestCase(
            pixels=single(3, 2, 1),
            expected=stated(bytes([0, 0, 0, THIRD_PIXEL]), b""),
            label="a row further down is a byte further on",
        ),
        TestCase(
            pixels=single(LAST_ROW, 0, 2),
            expected=stated(b"", bytes([0] * LAST_ROW + [LEFTMOST_PIXEL])),
            label="the bottom row of the high plane is the last byte",
        ),
        TestCase(
            pixels=single(3, 2, 3),
            expected=stated(bytes([0, 0, 0, THIRD_PIXEL]), bytes([0, 0, 0, THIRD_PIXEL])),
            label="entry three sets the pixel in both planes",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tile_is_written_low_plane_first(self, test_case: TestCase) -> None:
        assert tile_planes(test_case.pixels) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_bytes_read_back_as_the_tile(self, test_case: TestCase) -> None:
        assert planes_tile(test_case.expected) == test_case.pixels

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_tile_takes_sixteen_bytes(self, test_case: TestCase) -> None:
        assert len(tile_planes(test_case.pixels)) == TILE_BYTES

    def test_a_row_of_the_low_plane_holds_the_low_bit_of_each_pixel(self) -> None:
        assert plane_row(MIXED_ROW, LOW_PLANE_BIT) == MIXED_LOW_PLANE

    def test_a_row_of_the_high_plane_holds_the_high_bit_of_each_pixel(self) -> None:
        assert plane_row(MIXED_ROW, HIGH_PLANE_BIT) == MIXED_HIGH_PLANE


class TestATileReadBackFromItsBytes(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        pixels: Pixels

    test_cases = (
        TestCase(pixels=EMPTY, label="an empty tile"),
        TestCase(pixels=uniform(1), label="a tile of entry one"),
        TestCase(pixels=uniform(2), label="a tile of entry two"),
        TestCase(pixels=uniform(3), label="a tile of entry three"),
        TestCase(
            pixels=tuple(tuple(column % COLORS_PER_PALETTE for column in range(TILE_SIDE)) for _ in range(TILE_SIDE)),
            label="stripes along the rows",
        ),
        TestCase(
            pixels=tuple(tuple(row % COLORS_PER_PALETTE for _ in range(TILE_SIDE)) for row in range(TILE_SIDE)),
            label="stripes down the columns",
        ),
        TestCase(pixels=single(LAST_ROW, LAST_COLUMN, 3), label="one pixel in the last corner"),
        TestCase(pixels=scattered(SEED), label="scattered entries"),
        TestCase(pixels=scattered(SEED + 1), label="other scattered entries"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tile_survives_the_round_trip(self, test_case: TestCase) -> None:
        assert planes_tile(tile_planes(test_case.pixels)) == test_case.pixels


class TestThePatternTablesOfASheet(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        table: PatternTable

    test_cases = (
        TestCase(table=PatternTable.BACKGROUND, label="the background table"),
        TestCase(table=PatternTable.SPRITES, label="the sprite table"),
    )

    def test_both_tables_fill_the_pattern_memory(self, shipped_patterns: bytes) -> None:
        assert len(shipped_patterns) == PATTERNS_SIZE

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_table_reads_back_as_the_sheet_draws_it(
        self,
        test_case: TestCase,
        shipped_sheet: TileSheet,
        shipped_patterns: bytes,
    ) -> None:
        assert table_tiles(shipped_patterns, test_case.table) == shipped_sheet.drawn(test_case.table)

    def test_the_background_table_comes_first(self, shipped_sheet: TileSheet, shipped_patterns: bytes) -> None:
        background = b"".join(tile_planes(tile) for tile in shipped_sheet.drawn(PatternTable.BACKGROUND))
        sprites = b"".join(tile_planes(tile) for tile in shipped_sheet.drawn(PatternTable.SPRITES))

        assert background != sprites
        assert shipped_patterns[:PATTERN_TABLE_SIZE] == background
        assert shipped_patterns[PATTERN_TABLE_SIZE:] == sprites

    def test_the_same_sheet_draws_the_same_bytes(self, shipped_sheet: TileSheet, shipped_patterns: bytes) -> None:
        assert sheet_patterns(shipped_sheet) == shipped_patterns


class TestReadingAPatternTable(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        table: PatternTable
        tile: int

    test_cases = (
        TestCase(table=PatternTable.BACKGROUND, tile=0, label="the first background tile"),
        TestCase(table=PatternTable.BACKGROUND, tile=LAST_TILE, label="the last background tile"),
        TestCase(table=PatternTable.SPRITES, tile=0, label="the first sprite tile"),
        TestCase(table=PatternTable.SPRITES, tile=1, label="the second sprite tile"),
        TestCase(table=PatternTable.SPRITES, tile=LAST_TILE, label="the last sprite tile"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_tile_is_read_from_its_own_sixteen_bytes(self, test_case: TestCase) -> None:
        drawn = scattered(SEED)
        memory = bytearray(PATTERNS_SIZE)
        start = test_case.table * PATTERN_TABLE_SIZE + test_case.tile * TILE_BYTES
        memory[start : start + TILE_BYTES] = tile_planes(drawn)

        expected = [EMPTY] * TILES_PER_TABLE
        expected[test_case.tile] = drawn
        other = next(table for table in PatternTable if table is not test_case.table)

        assert table_tiles(bytes(memory), test_case.table) == tuple(expected)
        assert table_tiles(bytes(memory), other) == (EMPTY,) * TILES_PER_TABLE


class TestPatternsOfAnotherSize(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        size: int

    test_cases = (
        TestCase(size=0, label="nothing"),
        TestCase(size=PATTERN_TABLE_SIZE, label="one table alone"),
        TestCase(size=PATTERNS_SIZE - 1, label="a byte short"),
        TestCase(size=PATTERNS_SIZE + 1, label="a byte over"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_reading_a_table_out_of_them_is_refused(self, test_case: TestCase) -> None:
        with pytest.raises(ValueError, match=SIZE_REFUSAL):
            table_tiles(bytes(test_case.size), PatternTable.BACKGROUND)
