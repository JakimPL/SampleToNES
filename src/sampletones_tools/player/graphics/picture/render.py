from typing import Final

import numpy as np
from numpy.typing import NDArray

from sampletones_player.specification.screen import (
    ATTRIBUTE_CELL_TILES,
    ATTRIBUTE_CELLS_PER_BYTE,
    ATTRIBUTE_TABLE_SIDE,
    COLOR_BITS,
    COLORS_PER_PALETTE,
    HIDDEN_SPRITE_Y,
    PALETTES_PER_LAYER,
    SCREEN_COLUMNS,
    SCREEN_HEIGHT,
    SCREEN_ROWS,
    SCREEN_WIDTH,
    SPRITE_ATTRIBUTES_OFFSET,
    SPRITE_BYTES,
    SPRITE_COUNT,
    SPRITE_PALETTE_MASK,
    SPRITE_SCANLINE_DELAY,
    SPRITE_TILE_OFFSET,
    SPRITE_X_OFFSET,
    SPRITE_Y_OFFSET,
    TILE_SIDE,
)
from sampletones_tools.player.graphics.picture.colors import MasterPalette
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.patterns import table_tiles

BACKDROP_ENTRY: Final[int] = 0
SPRITE_ENTRIES_START: Final[int] = PALETTES_PER_LAYER * COLORS_PER_PALETTE
PALETTE_MASK: Final[int] = PALETTES_PER_LAYER - 1
ATTRIBUTE_BLOCK_TILES: Final[int] = ATTRIBUTE_CELL_TILES * ATTRIBUTE_CELLS_PER_BYTE


def background_palette(picture: Picture, row: int, column: int) -> int:
    """The palette the cell at ``row`` and ``column`` takes, read out of the attribute memory."""
    packed = picture.attributes[(row // ATTRIBUTE_BLOCK_TILES) * ATTRIBUTE_TABLE_SIDE + column // ATTRIBUTE_BLOCK_TILES]
    square = (row % ATTRIBUTE_BLOCK_TILES) // ATTRIBUTE_CELL_TILES * ATTRIBUTE_CELLS_PER_BYTE + (
        column % ATTRIBUTE_BLOCK_TILES
    ) // ATTRIBUTE_CELL_TILES
    return (packed >> (square * COLOR_BITS)) & PALETTE_MASK


def palette_entries(picture: Picture, patterns: bytes) -> NDArray[np.uint8]:
    """The palette memory entry every pixel of a picture shows.

    A background pixel a tile leaves empty shows the backdrop, and a sprite covers the background
    wherever its own pixel is drawn, an earlier sprite covering a later one.

    Args:
        picture: The video memory of one frame.
        patterns: Both pattern tables, as a cartridge carries them.

    Returns:
        NDArray[np.uint8]: One palette memory index per pixel, 240 rows of 256.

    Raises:
        ValueError: If ``patterns`` is another size than two pattern tables.
    """
    background = np.array(table_tiles(patterns, PatternTable.BACKGROUND), dtype=np.uint8)
    sprites = np.array(table_tiles(patterns, PatternTable.SPRITES), dtype=np.uint8)
    entries = np.full((SCREEN_HEIGHT, SCREEN_WIDTH), BACKDROP_ENTRY, dtype=np.uint8)

    for row in range(SCREEN_ROWS):
        for column in range(SCREEN_COLUMNS):
            tile = background[picture.nametable[row * SCREEN_COLUMNS + column]]
            colored = background_palette(picture, row, column) * COLORS_PER_PALETTE + tile
            top, left = row * TILE_SIDE, column * TILE_SIDE
            entries[top : top + TILE_SIDE, left : left + TILE_SIDE] = np.where(tile > 0, colored, BACKDROP_ENTRY)

    for sprite in reversed(range(SPRITE_COUNT)):
        start = sprite * SPRITE_BYTES
        if picture.sprites[start + SPRITE_Y_OFFSET] >= HIDDEN_SPRITE_Y - SPRITE_SCANLINE_DELAY:
            continue

        tile = sprites[picture.sprites[start + SPRITE_TILE_OFFSET]]
        palette = picture.sprites[start + SPRITE_ATTRIBUTES_OFFSET] & SPRITE_PALETTE_MASK
        top = picture.sprites[start + SPRITE_Y_OFFSET] + SPRITE_SCANLINE_DELAY
        left = picture.sprites[start + SPRITE_X_OFFSET]
        visible = entries[top : top + TILE_SIDE, left : left + TILE_SIDE]
        shown = tile[: visible.shape[0], : visible.shape[1]]
        colored = SPRITE_ENTRIES_START + palette * COLORS_PER_PALETTE + shown
        visible[...] = np.where(shown > 0, colored, visible)

    return entries


def render(picture: Picture, patterns: bytes, colors: MasterPalette) -> NDArray[np.uint8]:
    """The picture as a display shows it.

    Args:
        picture: The video memory of one frame.
        patterns: Both pattern tables, as a cartridge carries them.
        colors: The red, green and blue each of the console's colors is shown as.

    Returns:
        NDArray[np.uint8]: The frame as 240 rows of 256 pixels, three channels each.

    Raises:
        ValueError: If ``patterns`` is another size than two pattern tables.
    """
    shown = np.frombuffer(picture.palette, dtype=np.uint8)[palette_entries(picture, patterns)]
    rendered: NDArray[np.uint8] = colors.to_array()[shown]
    return rendered
