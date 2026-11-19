from dataclasses import dataclass
from typing import Final, Sequence, Tuple

import numpy as np
import pytest

from sampletones_player.specification.screen import (
    ATTRIBUTE_TABLE_SIZE,
    COLORS_PER_PALETTE,
    HIDDEN_SPRITE_Y,
    MASTER_COLOR_COUNT,
    NAMETABLE_SIZE,
    PALETTE_SIZE,
    PALETTES_PER_LAYER,
    PATTERNS_SIZE,
    SCREEN_COLUMNS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPRITE_COUNT,
    TILE_SIDE,
    TILES_PER_TABLE,
)
from sampletones_tools.player.graphics.picture.colors import MasterPalette
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.graphics.picture.render import background_palette, palette_entries, render
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.patterns import tile_planes
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

SpriteBytes = Tuple[int, int, int, int]

EMPTY_TILE: Final[int] = 0
SOLID_TILE: Final[int] = 1
CORNER_TILE: Final[int] = 2
SOLID_COLOR: Final[int] = 2
CORNER_COLOR: Final[int] = 3
SOLID: Final[Pixels] = ((SOLID_COLOR,) * TILE_SIDE,) * TILE_SIDE
CORNER: Final[Pixels] = ((CORNER_COLOR,) + (0,) * (TILE_SIDE - 1),) + ((0,) * TILE_SIDE,) * (TILE_SIDE - 1)
EMPTY: Final[Pixels] = ((0,) * TILE_SIDE,) * TILE_SIDE

ROW: Final[int] = 5
COLUMN: Final[int] = 6
TOP: Final[int] = ROW * TILE_SIDE
LEFT: Final[int] = COLUMN * TILE_SIDE
CELL_PALETTE: Final[int] = 2
CELL_BYTE: Final[int] = 9
CELL_SHIFT: Final[int] = 2
BACKDROP: Final[int] = 0
SPRITE_ENTRIES: Final[int] = PALETTES_PER_LAYER * COLORS_PER_PALETTE
SCANLINE_DELAY: Final[int] = 1
FIRST_SPRITE_PALETTE: Final[int] = 1
SECOND_SPRITE_PALETTE: Final[int] = 2
LAST_SPRITE_LEFT: Final[int] = SCREEN_WIDTH - TILE_SIDE // 2
PALETTE_STEP: Final[int] = 2


def table(tiles: Sequence[Pixels]) -> bytes:
    """A pattern table opening with ``tiles``, every tile after them empty."""
    drawn = [*tiles, *[EMPTY] * (TILES_PER_TABLE - len(tiles))]
    return b"".join(tile_planes(tile) for tile in drawn)


PATTERNS: Final[bytes] = table([EMPTY, SOLID, CORNER]) * 2
GRAYS: Final[MasterPalette] = MasterPalette(
    colors=((*[f"#{number:02X}{number:02X}{number:02X}" for number in range(MASTER_COLOR_COUNT)],),)
)
SHIFTED_PALETTE: Final[bytes] = bytes(entry * PALETTE_STEP % MASTER_COLOR_COUNT for entry in range(PALETTE_SIZE))


def picture(sprites: Sequence[SpriteBytes]) -> Picture:
    """A screen of empty cells with one solid cell, its palette set, and ``sprites`` first in memory."""
    nametable = bytearray(NAMETABLE_SIZE)
    nametable[ROW * SCREEN_COLUMNS + COLUMN] = SOLID_TILE
    attributes = bytearray(ATTRIBUTE_TABLE_SIZE)
    attributes[CELL_BYTE] = CELL_PALETTE << CELL_SHIFT
    hidden = [(HIDDEN_SPRITE_Y, EMPTY_TILE, 0, 0)] * (SPRITE_COUNT - len(sprites))
    return Picture(
        nametable=bytes(nametable),
        attributes=bytes(attributes),
        palette=SHIFTED_PALETTE,
        sprites=bytes(value for sprite in [*sprites, *hidden] for value in sprite),
    )


def sprite_entry(palette: int, color: int) -> int:
    return SPRITE_ENTRIES + palette * COLORS_PER_PALETTE + color


CELL_ENTRY: Final[int] = CELL_PALETTE * COLORS_PER_PALETTE + SOLID_COLOR


class TestTheBackgroundPaletteOfACell(BaseTestSuite):
    """An attribute byte colors a block of four by four cells, two bits for each square of two by two."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        row: int
        column: int
        shift: int

    test_cases = (
        TestCase(row=0, column=0, shift=0, label="the upper left square"),
        TestCase(row=0, column=2, shift=2, label="the upper right square"),
        TestCase(row=2, column=0, shift=4, label="the lower left square"),
        TestCase(row=3, column=3, shift=6, label="the lower right square"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_square_is_read_from_its_own_two_bits(self, test_case: TestCase) -> None:
        attributes = bytearray(ATTRIBUTE_TABLE_SIZE)
        attributes[0] = (PALETTES_PER_LAYER - 1) << test_case.shift
        shown = picture([]).model_copy(update={"attributes": bytes(attributes)})

        assert background_palette(shown, test_case.row, test_case.column) == PALETTES_PER_LAYER - 1

    def test_the_cell_of_the_shared_fixture_takes_its_palette(self) -> None:
        assert background_palette(picture([]), ROW, COLUMN) == CELL_PALETTE


class TestThePaletteEntries(BaseTestSuite):
    def test_every_pixel_has_an_entry(self) -> None:
        assert palette_entries(picture([]), PATTERNS).shape == (SCREEN_HEIGHT, SCREEN_WIDTH)

    def test_a_drawn_cell_shows_the_entry_of_its_palette_and_color(self) -> None:
        entries = palette_entries(picture([]), PATTERNS)

        assert (entries[TOP : TOP + TILE_SIDE, LEFT : LEFT + TILE_SIDE] == CELL_ENTRY).all()

    def test_every_empty_cell_shows_the_backdrop(self) -> None:
        entries = palette_entries(picture([]), PATTERNS)

        entries[TOP : TOP + TILE_SIDE, LEFT : LEFT + TILE_SIDE] = BACKDROP
        assert (entries == BACKDROP).all()

    def test_a_sprite_shows_one_scanline_below_the_position_it_states(self) -> None:
        sprite = (TOP, CORNER_TILE, FIRST_SPRITE_PALETTE, 0)

        entries = palette_entries(picture([sprite]), PATTERNS)

        assert entries[TOP + SCANLINE_DELAY, 0] == sprite_entry(FIRST_SPRITE_PALETTE, CORNER_COLOR)
        assert entries[TOP, 0] == BACKDROP

    def test_the_empty_pixels_of_a_sprite_leave_the_background_showing(self) -> None:
        sprite = (TOP - SCANLINE_DELAY, CORNER_TILE, FIRST_SPRITE_PALETTE, LEFT)

        entries = palette_entries(picture([sprite]), PATTERNS)

        assert entries[TOP, LEFT] == sprite_entry(FIRST_SPRITE_PALETTE, CORNER_COLOR)
        assert entries[TOP, LEFT + 1] == CELL_ENTRY

    def test_an_earlier_sprite_covers_a_later_one(self) -> None:
        first = (TOP, CORNER_TILE, FIRST_SPRITE_PALETTE, 0)
        second = (TOP, CORNER_TILE, SECOND_SPRITE_PALETTE, 0)

        entries = palette_entries(picture([first, second]), PATTERNS)

        assert entries[TOP + SCANLINE_DELAY, 0] == sprite_entry(FIRST_SPRITE_PALETTE, CORNER_COLOR)

    def test_a_hidden_sprite_draws_nothing(self) -> None:
        sprite = (HIDDEN_SPRITE_Y, SOLID_TILE, FIRST_SPRITE_PALETTE, LEFT)

        assert (palette_entries(picture([sprite]), PATTERNS) == palette_entries(picture([]), PATTERNS)).all()

    def test_a_sprite_reaching_past_the_right_edge_is_cut_at_it(self) -> None:
        sprite = (TOP, SOLID_TILE, FIRST_SPRITE_PALETTE, LAST_SPRITE_LEFT)

        entries = palette_entries(picture([sprite]), PATTERNS)

        row = entries[TOP + SCANLINE_DELAY]
        assert (row[LAST_SPRITE_LEFT:] == sprite_entry(FIRST_SPRITE_PALETTE, SOLID_COLOR)).all()

    def test_pattern_tables_of_another_size_are_refused(self) -> None:
        with pytest.raises(ValueError, match=str(PATTERNS_SIZE)):
            palette_entries(picture([]), PATTERNS[:-1])


class TestTheRenderedPicture(BaseTestSuite):
    def test_a_pixel_shows_the_color_its_palette_entry_holds(self) -> None:
        rendered = render(picture([]), PATTERNS, GRAYS)

        held = SHIFTED_PALETTE[CELL_ENTRY]
        assert tuple(rendered[TOP, LEFT]) == (held, held, held)

    def test_the_picture_is_the_console_frame_in_three_channels(self) -> None:
        rendered = render(picture([]), PATTERNS, GRAYS)

        assert rendered.shape == (SCREEN_HEIGHT, SCREEN_WIDTH, 3)
        assert rendered.dtype == np.uint8
