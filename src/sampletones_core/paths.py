from pathlib import Path
from typing import Final, Tuple

from platformdirs import user_config_dir, user_data_dir, user_documents_path

from sampletones_shared.application import (
    SAMPLETONES_GROUP,
    SAMPLETONES_NAME,
)

# User paths
USER_PATH_DOCUMENTS: Final[Path] = Path(user_documents_path()) / SAMPLETONES_NAME
USER_PATH_DATA: Final[Path] = Path(user_data_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))
USER_PATH_CONFIG: Final[Path] = Path(user_config_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))

# Application paths
LIBRARY_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "instructions"
RECONSTRUCTIONS_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "reconstructions"
PROJECTS_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "projects"
CONFIG_PATH: Final[Path] = USER_PATH_DOCUMENTS / "config.json"
APPLICATION_CONFIG_PATH: Final[Path] = USER_PATH_CONFIG / "config.yaml"

# File extensions
EXT_FILE_JSON: Final[str] = ".json"
EXT_FILE_YAML: Final[str] = ".yaml"
EXT_FILE_LIBRARY: Final[str] = ".ins"
EXT_FILE_INSTRUMENT: Final[str] = ".fti"
EXT_FILE_RECONSTRUCTION: Final[str] = ".stn"
EXT_FILE_PROJECT: Final[str] = ".stp"
EXT_FILE_MODULE: Final[str] = ".ftm"
EXT_FILE_WAVE: Final[str] = ".wav"
EXT_FILE_MP3: Final[str] = ".mp3"
EXT_FILE_FLAC: Final[str] = ".flac"
EXT_FILE_OGG: Final[str] = ".ogg"
EXT_FILE_AIFF: Final[str] = ".aiff"
EXT_FILE_AU: Final[str] = ".au"
EXT_FILES_AUDIO: Final[Tuple[str, ...]] = (
    EXT_FILE_WAVE,
    EXT_FILE_MP3,
    EXT_FILE_FLAC,
    EXT_FILE_OGG,
    EXT_FILE_AIFF,
    EXT_FILE_AU,
)

# Assets
ASSETS_DIRECTORY: Final[str] = "assets"

# Icon filenames
ICON_DIRECTORY: Final[str] = "icons"
ICON_WIN_FILENAME: Final[str] = "sampletones.ico"
ICON_UNIX_FILENAME: Final[str] = "sampletones.png"

# Font paths
FONT_DIRECTORY: Final[str] = "fonts"
FONT_SANS_REGULAR: Final[str] = "SourceSans3-Regular.ttf"
FONT_SANS_BOLD: Final[str] = "SourceSans3-Bold.ttf"
FONT_SANS_ITALIC: Final[str] = "SourceSans3-Italic.ttf"
FONT_MONO_REGULAR: Final[str] = "RobotoMono-Regular.ttf"
FONT_MONO_BOLD: Final[str] = "RobotoMono-Bold.ttf"
FONT_ICON: Final[str] = "DejaVuSans.ttf"

PROJECTS_DIRECTORY.mkdir(parents=True, exist_ok=True)
LIBRARY_DIRECTORY.mkdir(parents=True, exist_ok=True)
RECONSTRUCTIONS_DIRECTORY.mkdir(parents=True, exist_ok=True)
