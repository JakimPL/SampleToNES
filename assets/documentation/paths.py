from pathlib import Path
from typing import Final

from sampletones_shared.documentation.site import DOCUMENTATION_DIRECTORY
from sampletones_shared.paths.package import package_directory
from sampletones_shared.paths.resources import ASSETS_PACKAGE
from sampletones_shared.paths.source import REPOSITORY_ROOT, SOURCE_ROOT

STATIC_PACKAGE: Final[str] = "assets.documentation.static"

DOCS_DIRECTORY: Final[Path] = REPOSITORY_ROOT / "docs"
PROJECT_FILE: Final[Path] = REPOSITORY_ROOT / "pyproject.toml"
SITE_DIRECTORY: Final[Path] = SOURCE_ROOT / ASSETS_PACKAGE / DOCUMENTATION_DIRECTORY
STATIC_DIRECTORY: Final[Path] = package_directory(STATIC_PACKAGE)
