import sys
from importlib.resources import files
from pathlib import Path
from typing import Final, Optional

_BUNDLE_ROOT: Final[Optional[str]] = getattr(sys, "_MEIPASS", None)

CONFIG_DIRECTORY: Final[Path] = (
    Path(_BUNDLE_ROOT) / "config" if _BUNDLE_ROOT is not None else Path(str(files("sampletones_config")))
)
SOURCE_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT: Final[Path] = SOURCE_ROOT.parent
