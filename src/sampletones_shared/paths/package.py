from importlib.util import find_spec
from pathlib import Path


def package_directory(package: str) -> Path:
    """The directory an import package's files lie in, its data files among them.

    The import system's own record of where the package lives places it, which holds in a
    checkout, in an installed copy and in a bundle. PyInstaller unpacks a package's collected data
    into a directory of the package's name, which a package the application never imports as code
    reaches as a namespace package, so the location is read from the spec whatever kind of
    package answers.

    Args:
        package: The package's dotted name.

    Returns:
        Path: The directory.

    Raises:
        FileNotFoundError: If no package of that name is importable.
    """
    spec = find_spec(package)
    if spec is None or spec.submodule_search_locations is None:
        raise FileNotFoundError(f"No package {package} is importable to place its directory by")

    return Path(next(iter(spec.submodule_search_locations)))
