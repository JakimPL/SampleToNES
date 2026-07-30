from pathlib import Path
from typing import Final

import sampletones_application
import sampletones_config

# Root
APPLICATION_SOURCE_DIRECTORY: Final[Path] = Path(sampletones_application.__file__).parent
CONFIG_DIRECTORY: Final[Path] = Path(sampletones_config.__file__).parent
