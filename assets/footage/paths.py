from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.source import BUILD_ROOT

FOOTAGE_DIRECTORY: Final[Path] = BUILD_ROOT / "footage"
KEPT_DIRECTORY: Final[Path] = FOOTAGE_DIRECTORY / "records"
SCENES_DIRECTORY: Final[Path] = package_directory("assets.footage.scenes")
DEMO_SPECIFICATION: Final[Path] = package_directory("assets.footage.config") / "demo.yaml"
SOUNDTRACK_FILE: Final[str] = "soundtrack.wav"
FRAMES_FOLDER: Final[str] = "frames"
VIDEO_SUFFIX: Final[str] = ".mp4"
