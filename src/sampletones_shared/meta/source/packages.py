from pathlib import Path

from sampletones_shared.paths import SOURCE_ROOT


def package_directory(name: str, *parts: str) -> Path:
    """The directory a package occupies, named by path rather than by import.

    A source check reads the tree it checks, so taking a package from the source root keeps the
    check free of importing the code under it and free of the layout of any one installation.

    Args:
        name: Top-level package name.
        parts: Subpackage names, innermost last.

    Returns:
        Path: The directory the package occupies.

    Raises:
        NotADirectoryError: If the source root holds no directory at that path.
    """
    directory = SOURCE_ROOT.joinpath(name, *parts)
    if not directory.is_dir():
        raise NotADirectoryError(f"The source root {SOURCE_ROOT} holds no package directory at {directory}")

    return directory
