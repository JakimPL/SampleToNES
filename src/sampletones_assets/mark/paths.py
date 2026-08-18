from importlib.resources import files
from pathlib import Path
from typing import Final

MARK_DIRECTORY: Final[Path] = Path(str(files("sampletones_assets.mark")))
MARK_PATH: Final[Path] = MARK_DIRECTORY / "mark.yaml"
TEMPLATE_PATH: Final[Path] = MARK_DIRECTORY / "template.svg"
