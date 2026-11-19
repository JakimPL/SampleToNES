from typing import Final, Tuple

from sampletones_player.specification.screen import (
    PATTERN_TABLE_SIZE,
    PATTERNS_SIZE,
    TILE_BYTES,
    TILE_SIDE,
    TILES_PER_TABLE,
)
from sampletones_tools.player.graphics.sheet.drawing import Pixels
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet

LOW_PLANE_BIT: Final[int] = 0
HIGH_PLANE_BIT: Final[int] = 1
LEFTMOST_BIT: Final[int] = TILE_SIDE - 1


def plane_row(row: Tuple[int, ...], bit: int) -> int:
    """One row of a tile's bit plane: the chosen bit of each pixel, leftmost pixel in the top bit."""
    return sum(((color >> bit) & 1) << (LEFTMOST_BIT - column) for column, color in enumerate(row))


def tile_planes(pixels: Pixels) -> bytes:
    """The sixteen bytes a tile takes in a pattern table: its low bit plane, then its high one.

    Args:
        pixels: The tile's palette entries, eight rows of eight.

    Returns:
        bytes: The two planes, eight rows each.
    """
    return bytes([plane_row(row, bit) for bit in (LOW_PLANE_BIT, HIGH_PLANE_BIT) for row in pixels])


def planes_tile(planes: bytes) -> Pixels:
    """The palette entries a tile's sixteen pattern bytes draw.

    Args:
        planes: The tile's low bit plane followed by its high one.

    Returns:
        Pixels: Eight rows of eight entries.
    """
    return tuple(
        tuple(
            ((planes[row] >> (LEFTMOST_BIT - column)) & 1)
            | (((planes[TILE_SIDE + row] >> (LEFTMOST_BIT - column)) & 1) << HIGH_PLANE_BIT)
            for column in range(TILE_SIDE)
        )
        for row in range(TILE_SIDE)
    )


def sheet_patterns(sheet: TileSheet) -> bytes:
    """The pattern tables a cartridge carries for a sheet: the screen's table, then the sprites'.

    Args:
        sheet: The drawings and where each is placed.

    Returns:
        bytes: Both tables, each tile in its sixteen bytes.
    """
    return b"".join(tile_planes(tile) for table in PatternTable for tile in sheet.drawn(table))


def table_tiles(patterns: bytes, table: PatternTable) -> Tuple[Pixels, ...]:
    """Every tile one pattern table draws.

    Args:
        patterns: Both pattern tables, as a cartridge carries them.
        table: The table to read.

    Returns:
        Tuple[Pixels, ...]: The table's 256 tiles, in tile order.

    Raises:
        ValueError: If ``patterns`` is another size than two pattern tables.
    """
    if len(patterns) != PATTERNS_SIZE:
        raise ValueError(f"pattern tables take {PATTERNS_SIZE} bytes, got {len(patterns)}")

    start = table * PATTERN_TABLE_SIZE
    return tuple(
        planes_tile(patterns[start + tile * TILE_BYTES : start + (tile + 1) * TILE_BYTES])
        for tile in range(TILES_PER_TABLE)
    )
