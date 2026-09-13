import argparse
import sys
from pathlib import Path
from typing import Sequence

from bootstrap.files import remove_path
from bootstrap.layout import (
    CACHE_DIRECTORIES,
    CACHE_DIRECTORY_SUFFIXES,
    CACHE_FILE_SUFFIXES,
    CLEAN_ARTIFACTS,
    CLEAN_PATTERNS,
    ENVIRONMENTS,
    repository_root,
)


def remove_artifacts(root: Path) -> None:
    """Removes the build outputs and the coverage reports under ``root``."""
    for name in CLEAN_ARTIFACTS:
        remove_path(root / name)

    for pattern in CLEAN_PATTERNS:
        for path in root.glob(pattern):
            remove_path(path)


def remove_caches(root: Path) -> None:
    """Removes the bytecode caches and packaging leftovers under ``root``, the environments left alone."""
    for directory, subdirectories, files in root.walk():
        subdirectories[:] = [name for name in subdirectories if name not in ENVIRONMENTS]
        for name in list(subdirectories):
            if name in CACHE_DIRECTORIES or name.endswith(CACHE_DIRECTORY_SUFFIXES):
                remove_path(directory / name)
                subdirectories.remove(name)

        for name in files:
            if name.endswith(CACHE_FILE_SUFFIXES):
                remove_path(directory / name)


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
