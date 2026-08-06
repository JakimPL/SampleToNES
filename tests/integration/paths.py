from pathlib import Path
from typing import Final


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent

    raise RuntimeError("Could not locate the repository root")


REPO_ROOT: Final[Path] = _repo_root()
INTEGRATION_ROOT: Final[Path] = Path(__file__).parent

CONFIG_DIRECTORY: Final[Path] = INTEGRATION_ROOT / "config"
SYNTH_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "synth.yaml"
RECONSTRUCTION_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "reconstruction.yaml"
MODULE_CONFIG_PATH: Final[Path] = CONFIG_DIRECTORY / "module.yaml"
SONG_PATH: Final[Path] = CONFIG_DIRECTORY / "song.yaml"

MODULE_FILENAME: Final[str] = "drums.ftm"
FTM_OUTPUT_ENV: Final[str] = "SAMPLETONES_FTM_OUTPUT_DIR"

DOCUMENT_FILENAME: Final[str] = "drums.btp"
BTP_OUTPUT_ENV: Final[str] = "SAMPLETONES_BTP_OUTPUT_DIR"
