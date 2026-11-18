from pathlib import Path

from sampletones_player.specification.shell import PATTERNS_NAME
from sampletones_shared.utils.serialization import save_binary
from sampletones_tools.player.graphics.sheet.patterns import sheet_patterns
from sampletones_tools.player.graphics.sheet.sheet import TileSheet


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
