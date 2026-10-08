from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.source import REPOSITORY_ROOT

PICTURE_SUFFIX: Final[str] = ".webp"
IMAGES_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "docs" / "images"
GUIDE_DIRECTORY: Final[Path] = IMAGES_DIRECTORY / "guide"
README_PICTURE: Final[Path] = IMAGES_DIRECTORY / f"sampletones{PICTURE_SUFFIX}"
DEMO_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "build" / "demo"
KEPT_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "build" / "pictures"
HOMES_DIRECTORY: Final[Path] = KEPT_DIRECTORY / "homes"
SCENES_DIRECTORY: Final[Path] = package_directory("assets.pictures.scenes")


def guide_picture(page: str, name: str) -> Path:
    """Where the picture ``name`` of the guide page ``page`` is kept."""
    return GUIDE_DIRECTORY / page / f"{name}{PICTURE_SUFFIX}"
