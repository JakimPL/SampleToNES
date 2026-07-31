import sys
from importlib.resources import files
from pathlib import Path
from typing import Final, Optional

_BUNDLE_ROOT: Final[Optional[str]] = getattr(sys, "_MEIPASS", None)

CONFIG_DIRECTORY: Final[Path] = (
    Path(_BUNDLE_ROOT) / "config" if _BUNDLE_ROOT is not None else Path(str(files("sampletones_config")))
)
REPOSITORY_ROOT: Final[Path] = CONFIG_DIRECTORY.parents[1]
