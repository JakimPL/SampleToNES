from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

MARK_CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.assets.mark.config")
MARK_PATH: Final[Path] = MARK_CONFIG_DIRECTORY / "mark.yaml"
TEMPLATE_PATH: Final[Path] = MARK_CONFIG_DIRECTORY / "template.svg"
