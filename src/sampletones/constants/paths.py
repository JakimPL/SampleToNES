from pathlib import Path
from typing import Final, Tuple

from platformdirs import user_config_dir, user_data_dir, user_documents_path

from sampletones.constants.application import SAMPLETONES_GROUP, SAMPLETONES_NAME

# User paths
USER_PATH_DOCUMENTS: Final[Path] = Path(user_documents_path()) / SAMPLETONES_NAME
USER_PATH_DATA: Final[Path] = Path(user_data_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))
USER_PATH_CONFIG: Final[Path] = Path(user_config_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))

# Application paths
LIBRARY_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "library"
OUTPUT_DIRECTORY: Final[Path] = USER_PATH_DOCUMENTS / "reconstructions"
CONFIG_PATH: Final[Path] = USER_PATH_DOCUMENTS / "config.json"
APPLICATION_CONFIG_PATH: Final[Path] = USER_PATH_CONFIG / "sampletones.yaml"

# File extensions
EXT_FILE_JSON: Final[str] = ".json"
EXT_FILE_YAML: Final[str] = ".yaml"
EXT_FILE_LIBRARY: Final[str] = ".dat"
EXT_FILE_INSTRUMENT: Final[str] = ".fti"
EXT_FILE_RECONSTRUCTION: Final[str] = ".stn"
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
FONT_MAIN: Final[str] = "RobotoMono-Regular.ttf"
FONT_BOLD: Final[str] = "RobotoMono-Bold.ttf"
FONT_ITALIC: Final[str] = "RobotoMono-Italic.ttf"
FONT_BOLD_ITALIC: Final[str] = "RobotoMono-BoldItalic.ttf"
