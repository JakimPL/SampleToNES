import struct
from pathlib import Path
from typing import Final, Tuple

import numpy as np

from sampletones_player.specification.screen import SCREEN_HEIGHT, SCREEN_WIDTH, TILE_SIDE, TILES_PER_TABLE
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from sampletones_tools.player.graphics.preview import (
    PREVIEW_SCALE,
    SHEET_COLUMNS,
    enlarged,
    sheet_picture,
    write_previews,
)
from sampletones_tools.player.graphics.sheet.groups import PatternTable
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from tests.suite.base import BaseTestSuite

SCALE: Final[int] = 2
SIGNATURE: Final[bytes] = b"\x89PNG\r\n\x1a\n"
SIZE_START: Final[int] = 16
SIZE_END: Final[int] = 24
SHEET_SIDE: Final[int] = TILES_PER_TABLE // SHEET_COLUMNS * TILE_SIDE


def png_size(filepath: Path) -> Tuple[int, int]:
    """The width and height a PNG file states in its header chunk."""
    width, height = struct.unpack(">II", filepath.read_bytes()[SIZE_START:SIZE_END])
    return width, height


class TestAnEnlargedImage(BaseTestSuite):
    def test_every_pixel_is_repeated_both_ways(self) -> None:
        pixels = np.arange(4 * 3, dtype=np.uint8).reshape((2, 2, 3))

        scaled = enlarged(pixels, SCALE)

        assert scaled.shape == (2 * SCALE, 2 * SCALE, 3)
        assert all(
            (
                scaled[row * SCALE : (row + 1) * SCALE, column * SCALE : (column + 1) * SCALE] == pixels[row, column]
            ).all()
            for row in range(2)
            for column in range(2)
        )


class TestThePictureOfASheet(BaseTestSuite):
    def test_a_table_is_laid_out_as_a_square_grid_of_its_tiles(
        self,
        shipped_sheet: TileSheet,
        shipped_layout: ScreenLayout,
    ) -> None:
        for table in PatternTable:
            assert sheet_picture(shipped_sheet, shipped_layout, table).shape == (SHEET_SIDE, SHEET_SIDE, 3)


class TestTheWrittenPreviews(BaseTestSuite):
    def test_every_written_file_is_a_png(self, tmp_path: Path) -> None:
        written = write_previews(tmp_path)

        assert written
        assert all(filepath.read_bytes().startswith(SIGNATURE) for filepath in written)

    def test_the_two_screens_and_both_tables_are_written(self, tmp_path: Path) -> None:
        sizes = sorted(png_size(filepath) for filepath in write_previews(tmp_path))

        screen = (SCREEN_WIDTH * PREVIEW_SCALE, SCREEN_HEIGHT * PREVIEW_SCALE)
        sheet = (SHEET_SIDE * PREVIEW_SCALE, SHEET_SIDE * PREVIEW_SCALE)
        assert sizes == sorted([screen, screen, sheet, sheet])

    def test_a_missing_directory_is_created(self, tmp_path: Path) -> None:
        directory = tmp_path / "nested" / "previews"

        assert all(filepath.parent == directory for filepath in write_previews(directory))
