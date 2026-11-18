from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.source import BUILD_ROOT

FOOTAGE_DIRECTORY: Final[Path] = BUILD_ROOT / "footage"
DEMO_SPECIFICATION: Final[Path] = package_directory("assets.footage.config") / "demo.yaml"
SOUNDTRACK_FILE: Final[str] = "soundtrack.wav"
