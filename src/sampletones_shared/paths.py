from pathlib import Path
from typing import Final

# Root
ROOT_DIRECTORY: Final[Path] = Path(__file__).parents[2]
CONFIG_DIRECTORY: Final[Path] = ROOT_DIRECTORY / "sampletones_config"
