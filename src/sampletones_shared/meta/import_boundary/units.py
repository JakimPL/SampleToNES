from typing import Final, Iterable, Tuple

from sampletones_shared.meta.source.modules import MODULE_SEPARATOR

MODULE_SUFFIX: Final[str] = ".py"
PATH_SEPARATOR: Final[str] = "/"
UNIT_PATTERN: Final[str] = "**/*.py"


def unit_prefix(package: str, unit: str) -> str:
    """The import prefix a unit is reached by.

    Args:
        package: Import prefix the unit sits under, empty where the unit is a package itself.
        unit: Unit named as a path under the graph's root.

    Returns:
        str: The dotted prefix an import of that unit begins with.
    """
    name = unit.removesuffix(MODULE_SUFFIX).replace(
        PATH_SEPARATOR,
        MODULE_SEPARATOR,
    )
    return f"{package}{MODULE_SEPARATOR}{name}" if package else name


def unit_glob(unit: str) -> str:
    """The glob naming the modules a unit holds, whether the unit is a module or a directory."""
    return unit if unit.endswith(MODULE_SUFFIX) else f"{unit}{PATH_SEPARATOR}{UNIT_PATTERN}"


def nested_globs(unit: str, units: Iterable[str]) -> Tuple[str, ...]:
    """The globs of the units declared inside another one, which own their modules instead."""
    return tuple(unit_glob(other) for other in units if other.startswith(f"{unit}{PATH_SEPARATOR}"))
