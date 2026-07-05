from pathlib import Path
from typing import Final

import sampletones_config

# Root
ROOT_DIRECTORY: Final[Path] = Path(__file__).parents[2]
CONFIG_DIRECTORY: Final[Path] = Path(sampletones_config.__file__).parent
