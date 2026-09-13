from pathlib import Path
from typing import Final

from sampletones_shared.paths.package import package_directory

CONFIG_DIRECTORY: Final[Path] = package_directory("sampletones_tools.corpus.config")
SYNTH_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "synth.yaml"
CATALOG_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "reconstruction.yaml"
MODULE_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "module.yaml"
SONG_PATH: Final[Path] = CONFIG_DIRECTORY / "song.yaml"
