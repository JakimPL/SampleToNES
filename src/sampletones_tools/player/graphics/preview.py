from pathlib import Path
from typing import Dict, Final, List

import numpy as np
from numpy.typing import NDArray

from sampletones_player.specification.screen import TILE_SIDE, TILES_PER_TABLE
from sampletones_shared.application import SAMPLETONES_COPYRIGHT
from sampletones_shared.utils.png import write_png
from sampletones_tools.player.graphics.deck.deck import Deck
from sampletones_tools.player.graphics.deck.state import (
    DeckState,
    NoiseState,
    PulseState,
    Transport,
    TriangleState,
)
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from sampletones_tools.player.graphics.picture.colors import MasterPalette
from sampletones_tools.player.graphics.picture.picture import Picture
from sampletones_tools.player.graphics.picture.render import render
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.patterns import sheet_patterns
from sampletones_tools.player.graphics.sheet.sheet import TileSheet

PREVIEW_SCALE: Final[int] = 3
PREVIEW_SUFFIX: Final[str] = ".png"
RESTING_NAME: Final[str] = "deck-resting"
PLAYING_NAME: Final[str] = "deck-playing"
SHEET_NAME: Final[str] = "tiles"
SHEET_COLUMNS: Final[int] = 16
SHEET_PALETTE: Final[int] = 0
ROW_AXIS: Final[int] = 0
COLUMN_AXIS: Final[int] = 1

PLAYING: Final[DeckState] = DeckState(
    title="Amen Break",
    artist="SampleToNES",
    copyright=SAMPLETONES_COPYRIGHT,
    pulse1=PulseState(duty=1, level=11, pitch=49),
    pulse2=PulseState(duty=2, level=6, pitch=37),
    triangle=TriangleState(sounding=True, pitch=13),
    noise=NoiseState(level=9, period=6, short=False),
    played_seconds=83,
    total_seconds=225,
    progress=83,
    transport=Transport.PLAYING,
    shimmer=False,
)


def enlarged(pixels: NDArray[np.uint8], scale: int) -> NDArray[np.uint8]:
    """The image with every pixel repeated ``scale`` times each way, so single pixels stay sharp."""
    return pixels.repeat(scale, axis=ROW_AXIS).repeat(scale, axis=COLUMN_AXIS)


def sheet_picture(sheet: TileSheet, layout: ScreenLayout, table: PatternTable) -> NDArray[np.uint8]:
    """One pattern table laid out as a grid of its tiles, drawn in the screen's first palette."""
    tiles = np.array(sheet.drawn(table), dtype=np.uint8)
    rows = TILES_PER_TABLE // SHEET_COLUMNS
    grid = tiles.reshape((rows, SHEET_COLUMNS, TILE_SIDE, TILE_SIDE)).swapaxes(1, 2)
    entries = grid.reshape((rows * TILE_SIDE, SHEET_COLUMNS * TILE_SIDE))
    palettes = layout.palettes.background if table is PatternTable.BACKGROUND else layout.palettes.sprites
    shown = np.array(palettes[SHEET_PALETTE], dtype=np.uint8)[entries]
    pictured: NDArray[np.uint8] = MasterPalette.load().to_array()[shown]
    return pictured


def write_previews(directory: Path) -> List[Path]:
    """Renders the screen the package ships into pictures a person can review.

    The directory receives the resting screen, a screen showing a song in full flow, and both
    pattern tables as grids of tiles, each enlarged so single pixels stay visible.

    Args:
        directory: The directory receiving the pictures.

    Returns:
        List[Path]: The files written.

    Raises:
        OSError: If the directory cannot be written.
    """
    sheet = TileSheet.load()
    layout = ScreenLayout.load()
    deck = Deck(layout, sheet)
    patterns = sheet_patterns(sheet)
    colors = MasterPalette.load()

    pictures: Dict[str, Picture] = {RESTING_NAME: deck.resting(), PLAYING_NAME: deck.showing(PLAYING)}
    images: Dict[str, NDArray[np.uint8]] = {
        name: render(picture, patterns, colors) for name, picture in pictures.items()
    }
    for table in PatternTable:
        images[f"{SHEET_NAME}-{table.name.lower()}"] = sheet_picture(sheet, layout, table)

    directory.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []
    for name, image in images.items():
        filepath = (directory / name).with_suffix(PREVIEW_SUFFIX)
        write_png(filepath, enlarged(image, PREVIEW_SCALE))
        written.append(filepath)

    return written
