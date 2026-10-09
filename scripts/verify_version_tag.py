import argparse
import sys
from typing import Optional, Sequence

from bootstrap.layout import repository_root
from bootstrap.project import TAG_PREFIX, Project, read_project


def version_from_tag(tag: str) -> str:
    """The project version a release tag names, read from the tag with its ``v`` prefix dropped."""
    return tag.removeprefix(TAG_PREFIX)


def tag_failure(tag: str, project: Project) -> Optional[str]:
    """What keeps a release tag from publishing the project, or ``None`` for a tag naming its version.

    Args:
        tag: The release tag being built, such as ``v0.3.0``.
        project: The project the tag publishes.

    Returns:
        Optional[str]: The failure as one line, or ``None``.
    """
    if version_from_tag(tag) == project.version:
        return None

    return f"Tag {tag} names a version other than the project version {project.version}"


def main(argv: Sequence[str]) -> int:
    """Confirms a release tag names the version ``pyproject.toml`` records."""
    parser = argparse.ArgumentParser(description="Compare a release tag against the project version.")
    parser.add_argument("--tag", required=True, help="the release tag being built, such as v0.3.0")
    arguments = parser.parse_args(list(argv))

    tag: str = arguments.tag
    project = read_project(repository_root())
    failure = tag_failure(tag, project)
    if failure is not None:
        print(f"::error::{failure}")
        return 1

    print(f"Version {project.version} matches tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
