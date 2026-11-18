from importlib import resources

from sampletones_player.specification.screen import PATTERNS_SIZE
from sampletones_player.specification.shell import PATTERNS_NAME, SHELL_BINARY_DIRECTORY, SHELL_PACKAGE


def load_patterns() -> bytes:
    """Reads the tiles the package ships: the screen's pattern table, then the sprites'.

    Raises:
        ValueError: If the committed tiles take another size than two pattern tables.
    """
    patterns = (resources.files(SHELL_PACKAGE) / SHELL_BINARY_DIRECTORY / PATTERNS_NAME).read_bytes()
    if len(patterns) != PATTERNS_SIZE:
        raise ValueError(f"pattern tables take {PATTERNS_SIZE} bytes, got {len(patterns)}")

    return patterns
