from importlib.resources import files
from pathlib import Path
from typing import Final

CONFIG_DIRECTORY: Final[Path] = Path(str(files("sampletones_tools.corpus.config")))
SYNTH_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "synth.yaml"
CATALOG_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "reconstruction.yaml"
MODULE_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "module.yaml"
SONG_PATH: Final[Path] = CONFIG_DIRECTORY / "song.yaml"
