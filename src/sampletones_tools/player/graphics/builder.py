from pathlib import Path
from typing import Final

from sampletones_player.specification.shell import PATTERNS_NAME
from sampletones_shared.utils.serialization import save_binary
from sampletones_tools.player.assembler.layout import DECK_INCLUDE_NAME, DECK_SOURCE_NAME
from sampletones_tools.player.graphics.layout.screen import ScreenLayout
from sampletones_tools.player.graphics.sheet.patterns import sheet_patterns
from sampletones_tools.player.graphics.sheet.sheet import TileSheet
from sampletones_tools.player.graphics.shell.data import shell_data
from sampletones_tools.player.graphics.shell.listing import include_text, source_text

TEXT_ENCODING: Final[str] = "utf-8"


def build_patterns(destination: Path) -> bytes:
    """Draws the tile sheet into the pattern tables a cartridge carries and writes them out.

    Args:
        destination: The directory receiving ``patterns.bin``.

    Returns:
        bytes: Both pattern tables, as written.

    Raises:
        ValueError: If the sheet names a tile nothing draws, or places two tiles at one number.
        OSError: If the destination cannot be written.
    """
    patterns = sheet_patterns(TileSheet.load())
    destination.mkdir(parents=True, exist_ok=True)
    save_binary(destination / PATTERNS_NAME, patterns)
    return patterns


def build_shell_data(include_directory: Path, source_directory: Path) -> None:
    """Writes the screen the way the shell draws it: ``deck.inc`` with its equates, ``deck.s`` with its tables.

    Args:
        include_directory: The directory receiving the equates.
        source_directory: The directory receiving the tables.

    Raises:
        ValueError: If the sheet or the deck departs from a rule the shell draws by.
        OSError: If a destination cannot be written.
    """
    data = shell_data(ScreenLayout.load(), TileSheet.load())
    for directory, name, text in (
        (include_directory, DECK_INCLUDE_NAME, include_text(data)),
        (source_directory, DECK_SOURCE_NAME, source_text(data)),
    ):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_text(text, encoding=TEXT_ENCODING)
