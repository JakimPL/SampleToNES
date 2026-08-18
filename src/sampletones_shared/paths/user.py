from pathlib import Path
from typing import Final

from platformdirs import user_config_dir, user_data_dir, user_documents_path

from sampletones_shared.application import (
    SAMPLETONES_GROUP,
    SAMPLETONES_NAME,
)

USER_PATH_DOCUMENTS: Final[Path] = Path(user_documents_path()) / SAMPLETONES_NAME
USER_PATH_DATA: Final[Path] = Path(user_data_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))
USER_PATH_CONFIG: Final[Path] = Path(user_config_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))

LIBRARY_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "instructions"
RECONSTRUCTIONS_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "reconstructions"
PROJECTS_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "projects"
CONFIG_PATH: Final[Path] = USER_PATH_DOCUMENTS / "config.json"
APPLICATION_CONFIG_PATH: Final[Path] = USER_PATH_CONFIG / "config.yaml"

PROJECTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
LIBRARY_DIRECTORY.mkdir(parents=True, exist_ok=True)
RECONSTRUCTIONS_DIRECTORY.mkdir(parents=True, exist_ok=True)
