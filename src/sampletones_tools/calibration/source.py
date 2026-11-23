from pathlib import Path
from typing import Final, List, Sequence, Tuple

from .digest import sha256_digest

CACHE_DIRECTORY: Final[str] = "__pycache__"
HIDDEN_PREFIX: Final[str] = "."
ENTRY_SEPARATOR: Final[str] = " "
LINE_SEPARATOR: Final[str] = "\n"
EVERY_ENTRY: Final[str] = "*"


def source_digest(directories: Sequence[Path], version: str) -> str:
    """The digest of a program's source: its version, then every file its packages ship.

    A resumed run trusts a record only where the source that made it is unchanged, so the digest
    moves with any edit to a module or to a configuration file the packages carry. It is the digest
    of a manifest: the version on the first line, then a line per file holding the digest of the
    file's bytes beside the file's name.

    - A file is named by its path from the folder holding its package, written with forward
      slashes, so the digest reads alike wherever the program is installed and on every platform.
    - The lines follow the order of the names, so the digest stays the same whatever order the file
      system lists the files in.
    - A package ships every file beneath its directory outside ``__pycache__`` and the entries
      whose names begin with a dot, where the interpreter and the developer tools keep their
      caches, so the digest stays the same while the same source runs and is checked.
    - The version leads, so a build carrying its modules compiled outside its package directories,
      such as a bundle, still tells its releases apart.

    Args:
        directories: The directories of the packages, each named after its package.
        version: The version the program declares.

    Returns:
        str: The digest in hexadecimal.
    """
    lines = (_manifest_line(name, file) for name, file in _named_files(directories))
    return sha256_digest(LINE_SEPARATOR.join((version, *lines)).encode())


def _named_files(directories: Sequence[Path]) -> List[Tuple[str, Path]]:
    """Every file the packages in ``directories`` ship beside its name, in the order of the names."""
    return sorted(_named_file(file, directory) for directory in directories for file in _shipped_files(directory))


def _manifest_line(name: str, file: Path) -> str:
    """The manifest's line for a file: the digest of its bytes beside its name."""
    return f"{sha256_digest(file.read_bytes())}{ENTRY_SEPARATOR}{name}"


def _shipped_files(directory: Path) -> List[Path]:
    """The files the package in ``directory`` ships: every file beneath it outside the caches."""
    return [
        path
        for path in directory.rglob(EVERY_ENTRY)
        if path.is_file() and all(_shipped_entry(part) for part in path.relative_to(directory).parts)
    ]


def _shipped_entry(name: str) -> bool:
    """Whether an entry named ``name`` belongs to the package, which every entry but a cache does."""
    return name != CACHE_DIRECTORY and not name.startswith(HIDDEN_PREFIX)


def _named_file(file: Path, directory: Path) -> Tuple[str, Path]:
    """The file beside its name in the manifest: its path from the folder holding its package."""
    return file.relative_to(directory.parent).as_posix(), file
