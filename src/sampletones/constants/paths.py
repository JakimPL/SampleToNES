from pathlib import Path

from platformdirs import user_config_dir, user_data_dir, user_documents_path

from sampletones.constants.application import SAMPLETONES_GROUP, SAMPLETONES_NAME

# User paths
USER_PATH_DOCUMENTS = Path(user_documents_path()) / SAMPLETONES_NAME
USER_PATH_DATA = Path(user_data_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))
USER_PATH_CONFIG = Path(user_config_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))

# Application paths
LIBRARY_DIRECTORY = USER_PATH_DOCUMENTS / "library"
OUTPUT_DIRECTORY = USER_PATH_DOCUMENTS / "reconstructions"
CONFIG_PATH = USER_PATH_DOCUMENTS / "config.json"
APPLICATION_CONFIG_PATH = USER_PATH_CONFIG / "sampletones.yaml"

# File extensions
EXT_FILE_JSON = ".json"
EXT_FILE_YAML = ".yaml"
EXT_FILE_LIBRARY = ".dat"
EXT_FILE_INSTRUMENT = ".fti"
EXT_FILE_WAVE = ".wav"
EXT_FILE_RECONSTRUCTION = ".stn"

# Icon filenames
ICON_WIN_FILENAME = "sampletones.ico"
ICON_UNIX_FILENAME = "sampletones.png"
