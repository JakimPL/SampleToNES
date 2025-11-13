from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

from sampletones.constants.application import SAMPLETONES_GROUP, SAMPLETONES_NAME

USER_PATH_DATA = Path(user_data_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))
USER_PATH_CONFIG = Path(user_config_dir(SAMPLETONES_NAME, SAMPLETONES_GROUP))

LIBRARY_DIRECTORY = USER_PATH_DATA / "library"
OUTPUT_DIRECTORY = USER_PATH_DATA / "reconstructions"
CONFIG_PATH = USER_PATH_DATA / "config.json"

# File extensions
EXT_FILE_JSON = ".json"
EXT_FILE_LIBRARY = ".dat"
EXT_FILE_FTI = ".fti"
EXT_FILE_WAV = ".wav"
