from pathlib import Path
from typing import Final

REPOSITORY_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
ENTRY_PACKAGE: Final[Path] = REPOSITORY_ROOT / "src" / "sampletones"


def repository_root() -> Path:
    """The repository the scripts belong to, which every build and clean-up runs against.

    Raises:
        FileNotFoundError: If the scripts lie outside a SampleToNES checkout.
    """
    if not ENTRY_PACKAGE.is_dir():
        raise FileNotFoundError(f"SampleToNES project root not found (expected {ENTRY_PACKAGE})")

    return REPOSITORY_ROOT
