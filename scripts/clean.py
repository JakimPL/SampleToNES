import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Final, Sequence, Tuple

from bootstrap.repository import repository_root

ARTIFACTS: Final[Tuple[str, ...]] = ("bin", "build", "dist", "htmlcov", ".coverage")
ARTIFACT_PATTERNS: Final[Tuple[str, ...]] = ("*.spec",)
CACHE_DIRECTORIES: Final[Tuple[str, ...]] = ("__pycache__",)
CACHE_DIRECTORY_SUFFIXES: Final[Tuple[str, ...]] = (".egg-info",)
CACHE_FILE_SUFFIXES: Final[Tuple[str, ...]] = (".pyc",)
LEFT_ALONE: Final[Tuple[str, ...]] = (".git", ".venv", ".venv-build")


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def remove_artifacts(root: Path) -> None:
    """Removes the build outputs and the coverage reports under ``root``."""
    for name in ARTIFACTS:
        _remove(root / name)

    for pattern in ARTIFACT_PATTERNS:
        for path in root.glob(pattern):
            _remove(path)


def remove_caches(root: Path) -> None:
    """Removes the bytecode caches and packaging leftovers under ``root``, the environments left alone."""
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = [name for name in subdirectories if name not in LEFT_ALONE]
        for name in list(subdirectories):
            if name in CACHE_DIRECTORIES or name.endswith(CACHE_DIRECTORY_SUFFIXES):
                shutil.rmtree(Path(directory) / name)
                subdirectories.remove(name)

        for name in files:
            if name.endswith(CACHE_FILE_SUFFIXES):
                (Path(directory) / name).unlink()


def main(argv: Sequence[str]) -> int:
    """Removes the build artifacts and cache files from the repository."""
    parser = argparse.ArgumentParser(description="Remove build artifacts and cache files.")
    parser.parse_args(list(argv))

    root = repository_root()
    print("Removing build artifacts and temporary files...")
    remove_artifacts(root)
    remove_caches(root)
    print("Cleaned build artifacts and temporary files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
