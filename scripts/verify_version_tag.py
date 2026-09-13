import argparse
import sys
from typing import Final, Sequence

from bootstrap.layout import repository_root
from bootstrap.project import read_project

TAG_PREFIX: Final[str] = "v"


def version_from_tag(tag: str) -> str:
    """The project version a release tag names, read from the tag with its ``v`` prefix dropped."""
    return tag.removeprefix(TAG_PREFIX)


def main(argv: Sequence[str]) -> int:
    """Confirms a release tag names the version ``pyproject.toml`` records."""
    parser = argparse.ArgumentParser(description="Compare a release tag against the project version.")
    parser.add_argument("--tag", required=True, help="the release tag being built, such as v0.3.0")
    arguments = parser.parse_args(list(argv))

    tag: str = arguments.tag
    version = read_project(repository_root()).version
    if version_from_tag(tag) != version:
        print(f"::error::Tag {tag} names a version other than the project version {version}")
        return 1

    print(f"Version {version} matches tag {tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
