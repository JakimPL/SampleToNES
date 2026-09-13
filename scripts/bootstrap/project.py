import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, Tuple

from bootstrap.layout import PROJECT_FILE, SOURCE_DIRECTORY

BUILD_EXTRA: Final[str] = "build"
GPU_EXTRA: Final[str] = "gpu"
GPU_CUDA11_EXTRA: Final[str] = "gpu-cuda11"
DEVELOPMENT_GROUP: Final[str] = "dev"
NAMED_EXTRAS: Final[Tuple[str, ...]] = (BUILD_EXTRA, GPU_EXTRA, GPU_CUDA11_EXTRA)
NAMED_GROUPS: Final[Tuple[str, ...]] = (DEVELOPMENT_GROUP,)
ENTRY_SEPARATOR: Final[str] = ":"
MODULE_SEPARATOR: Final[str] = "."
MODULE_SUFFIX: Final[str] = ".py"


@dataclass(frozen=True)
class Project:
    """What ``pyproject.toml`` states that a build, a setup and a release gate read.

    Attributes:
        name: The distribution's name, which the command and the bundle carry too.
        version: The version a release is tagged with.
        entry_module: The module the command runs, read from ``[project.scripts]``.
        packages: The import packages the wheel carries.
        extras: The optional-dependency extras.
        groups: The dependency groups.
    """

    name: str
    version: str
    entry_module: str
    packages: Tuple[str, ...]
    extras: Tuple[str, ...]
    groups: Tuple[str, ...]

    @property
    def entry_script(self) -> str:
        """The entry module as a path from the repository root, which PyInstaller starts from."""
        return f"{SOURCE_DIRECTORY}/{self.entry_module.replace(MODULE_SEPARATOR, '/')}{MODULE_SUFFIX}"


def parse_project(document: Dict[str, Any]) -> Project:
    """The project a parsed ``pyproject.toml`` states, held to the names the scripts rely on.

    Args:
        document: The file as ``tomllib`` reads it.

    Returns:
        Project: The project.

    Raises:
        SystemExit: If the file lacks the command, an extra or a group the scripts name.
    """
    table = document["project"]
    name: str = table["name"]
    scripts: Dict[str, str] = table.get("scripts", {})
    if name not in scripts:
        raise SystemExit(f"ERROR: {PROJECT_FILE} names no '{name}' command under [project.scripts].")

    project = Project(
        name=name,
        version=table["version"],
        entry_module=scripts[name].split(ENTRY_SEPARATOR, 1)[0],
        packages=tuple(
            Path(package).name for package in document["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
        ),
        extras=tuple(table.get("optional-dependencies", {})),
        groups=tuple(document.get("dependency-groups", {})),
    )
    missing = [extra for extra in NAMED_EXTRAS if extra not in project.extras]
    missing.extend(group for group in NAMED_GROUPS if group not in project.groups)
    if missing:
        raise SystemExit(f"ERROR: {PROJECT_FILE} lacks what the scripts install: {', '.join(missing)}.")

    return project


def read_project(root: Path) -> Project:
    """The project the repository at ``root`` states.

    Raises:
        SystemExit: If the file lacks the command, an extra or a group the scripts name.
    """
    with (root / PROJECT_FILE).open("rb") as handle:
        return parse_project(tomllib.load(handle))
