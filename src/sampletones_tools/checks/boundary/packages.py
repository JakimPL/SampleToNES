from pathlib import Path
from typing import Final, List, Optional, Set, Tuple

from sampletones_tools.checks.boundary.units import INITIALIZER_FILENAME
from sampletones_tools.checks.boundary.violation import Violation
from sampletones_tools.checks.source.modules import source_paths

NAMESPACE_PACKAGE: Final[str] = "namespace package"


def enclosing_directories(module: Path, root: Path) -> Tuple[Path, ...]:
    """The directories a module sits in below the root, innermost first.

    Args:
        module: Module under the root.
        root: Directory the walk stops at, left out of the answer.

    Returns:
        Tuple[Path, ...]: Every directory between the root and the module.

    Raises:
        ValueError: If the module sits outside the root.
    """
    return tuple(root / directory for directory in module.relative_to(root).parents[:-1])


def check_packages(source: Path, selection: Optional[Set[Path]]) -> List[Violation]:
    """Every directory under the source root that holds modules and no initializer.

    Every directory between the source root and a module is a package with an `__init__.py` of
    its own. A directory holding modules alone is a namespace package, and a tool reading the tree
    takes it for a root it imports from. A module inside one then answers for the top-level module
    of the same name, the standard library's included, so the rule keeps every module reachable by
    its full name alone.

    Args:
        source: Source root the packages sit under.
        selection: Resolved paths to narrow the check to, or `None` to check the whole tree. A
            directory is reported where a selected module sits inside it.

    Returns:
        List[Violation]: One violation per directory, in path order.

    Raises:
        NotADirectoryError: If the source root names no directory.
        FileNotFoundError: If the source root holds no module to read.
    """
    root = source.resolve()
    modules = [path.resolve() for path in source_paths([root])]
    if selection is not None:
        modules = [module for module in modules if module in selection]

    directories = {directory for module in modules for directory in enclosing_directories(module, root)}
    return [
        Violation(
            kind=NAMESPACE_PACKAGE,
            location=str(directory),
        )
        for directory in sorted(directories)
        if not (directory / INITIALIZER_FILENAME).is_file()
    ]
