from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Sequence, Set

from sampletones_core.project.container import ProjectContainer
from sampletones_core.project.project import Project

LOADED_PURPOSE: Final[str] = "The project saved in `{path}`."
COUNTED_NAME: Final[str] = "{stem}-{count}"
FIRST_COUNT: Final[int] = 2


@dataclass(frozen=True)
class CheckedProject:
    """One project a tracker playback check plays, with what it is.

    Attributes:
        name: The name its files are written under.
        purpose: What the project exercises, or the file it was loaded from, in one sentence.
        project: The project itself.
    """

    name: str
    purpose: str
    project: Project


def loaded_projects(paths: Sequence[Path]) -> List[CheckedProject]:
    """The projects saved in the files a check is given, each named after its file.

    A file whose name an earlier file already took is named with a count after it, so the files each
    project writes stay apart.

    Args:
        paths: The project files, in the order the check plays them.

    Returns:
        List[CheckedProject]: One project per file, in the same order.

    Raises:
        LoadProjectError: If a file holds no project the application opens.
        OSError: If a file can't be read.
    """
    taken: Set[str] = set()
    projects: List[CheckedProject] = []
    for path in paths:
        name = unique_name(path.stem, taken)
        taken.add(name)
        projects.append(
            CheckedProject(
                name=name,
                purpose=LOADED_PURPOSE.format(path=path.resolve()),
                project=ProjectContainer.load(path),
            )
        )

    return projects


def unique_name(stem: str, taken: Set[str]) -> str:
    """``stem``, or ``stem`` with the lowest count from ``FIRST_COUNT`` up that no project took yet.

    Args:
        stem: The name the file gives.
        taken: The names earlier projects took.

    Returns:
        str: A name none of them has.
    """
    name = stem
    count = FIRST_COUNT
    while name in taken:
        name = COUNTED_NAME.format(stem=stem, count=count)
        count += 1

    return name
