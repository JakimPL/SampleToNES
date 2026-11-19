from pathlib import Path
from typing import Final

SOURCE_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT: Final[Path] = SOURCE_ROOT.parent
TESTS_ROOT: Final[Path] = REPOSITORY_ROOT / "tests"
BUILD_ROOT: Final[Path] = REPOSITORY_ROOT / "build"
