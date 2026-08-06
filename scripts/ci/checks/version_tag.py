import argparse
import sys
from typing import Final, Sequence

TAG_PREFIX: Final[str] = "v"


def version_from_tag(tag: str) -> str:
    """The project version a release tag names, read from the tag with its ``v`` prefix dropped."""
    return tag.removeprefix(TAG_PREFIX)


def tag_names_version(*, tag: str, project_version: str) -> bool:
    """Whether a release tag names the version recorded in the project metadata."""
    return version_from_tag(tag) == project_version


def main(argv: Sequence[str]) -> int:
    """Confirm a release tag and the project metadata agree on the version being released."""
    parser = argparse.ArgumentParser(
        description="Compare a release tag against the project version.",
    )
    parser.add_argument(
        "--tag",
        required=True,
        help="the release tag being built, such as v0.3.0",
    )
    parser.add_argument(
        "--project-version",
        required=True,
        help="the version recorded in pyproject.toml",
    )
    arguments = parser.parse_args(list(argv))

    tag: str = arguments.tag
    project_version: str = arguments.project_version
    if not tag_names_version(tag=tag, project_version=project_version):
        print(f"::error::Tag {tag} names a version other than the pyproject version {project_version}")
        return 1

    print(f"Version {project_version} matches tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
