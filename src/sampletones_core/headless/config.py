from pathlib import Path
from typing import Optional

from sampletones_core.configs import Config


def load_config(path: Optional[Path]) -> Config:
    """The configuration a headless run uses: the file named, or the saved one with the defaults behind it."""
    return Config.load(path) if path is not None else Config.default()
