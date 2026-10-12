from importlib import metadata
from typing import Final

from sampletones_shared.application import SAMPLETONES_NAME, SAMPLETONES_PACKAGE_NAME

SAMPLETONES_VERSION: Final[str] = metadata.version(SAMPLETONES_PACKAGE_NAME)
SAMPLETONES_NAME_VERSION: Final[str] = f"{SAMPLETONES_NAME} v{SAMPLETONES_VERSION}"
