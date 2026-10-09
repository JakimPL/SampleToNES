from pathlib import Path
from typing import Final

from sampletones_shared.paths.user import PROJECTS_DIRECTORY, RECONSTRUCTIONS_DIRECTORY

ARCHIVED_RECONSTRUCTION: Final[Path] = RECONSTRUCTIONS_DIRECTORY / "Archived.stn"
ARCHIVED_PROJECT: Final[Path] = PROJECTS_DIRECTORY / "Archived.stp"
VANISHED: Final[str] = "vanished"
SAMPLES_FIELD: Final[str] = "samples"
NAME_FIELD: Final[str] = "name"
BY_CONFIGURATION: Final[str] = "global.browser.label.by_configuration"
