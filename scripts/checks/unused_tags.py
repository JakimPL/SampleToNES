#!/usr/bin/env python3

"""
Checks that every tag fragment the tags package declares is read somewhere.

A tag or a suffix nobody reads still reads as part of the interface vocabulary, so it invites a
second constant for the same widget. The check counts reads across the sources, the tests, and the
scripts: a fragment feeding another fragment's value counts as read, while an import alone does not,
which is what makes a re-exported yet unread fragment visible.

Usage:
    python check_unused_tags.py
"""

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Final, List, NamedTuple, Sequence, Tuple

from sampletones_shared.meta.source.constants import module_constants
from sampletones_shared.meta.source.modules import SourceModule, discover_modules
from sampletones_shared.meta.source.references import count_identifier_loads
from sampletones_shared.paths import REPOSITORY_ROOT

SOURCE_ROOT: Final[Path] = REPOSITORY_ROOT / "src"
TAGS_PACKAGE: Final[Path] = SOURCE_ROOT / "sampletones_application" / "tags"
REFERENCE_ROOTS: Final[Tuple[Path, ...]] = (
    SOURCE_ROOT,
    REPOSITORY_ROOT / "tests",
    REPOSITORY_ROOT / "scripts",
)

FRAGMENT_PREFIXES: Final[Tuple[str, ...]] = ("TAG_", "SUF_", "PRE_")


class Fragment(NamedTuple):
    """One tag fragment a module declares, and where it declares it."""

    name: str
    location: str


def is_fragment(name: str) -> bool:
    """Whether a constant name belongs to the tag vocabulary."""
    return name.startswith(FRAGMENT_PREFIXES)


def declared_fragments(modules: Sequence[SourceModule]) -> List[Fragment]:
    """Every tag fragment the given modules declare, in the order they were read.

    Args:
        modules: Modules of the tags package.

    Returns:
        List[Fragment]: The fragments, each paired with its location.
    """
    return [
        Fragment(
            name=constant.name,
            location=f"{module.path}:{constant.line}",
        )
        for module in modules
        for constant in module_constants(module.tree)
        if is_fragment(constant.name)
    ]


def reference_counts(modules: Sequence[SourceModule]) -> Dict[str, int]:
    """How often the given modules read each identifier, summed across them.

    Args:
        modules: Modules to read.

    Returns:
        Dict[str, int]: Identifier to the number of reads.
    """
    counts: Counter[str] = Counter()
    for module in modules:
        counts.update(count_identifier_loads(module.tree))

    return dict(counts)


def unread_fragments(
    fragments: Sequence[Fragment],
    counts: Dict[str, int],
) -> List[Fragment]:
    """The fragments no module reads.

    Args:
        fragments: Fragments the tags package declares.
        counts: Reads per identifier, as `reference_counts` states them.

    Returns:
        List[Fragment]: The fragments standing at no reads, in the order they were declared.
    """
    return [fragment for fragment in fragments if counts.get(fragment.name, 0) == 0]


def main(argv: Sequence[str]) -> int:
    """Report every tag fragment the repository declares and never reads."""
    parser = argparse.ArgumentParser(
        description="Check that every declared tag fragment is read somewhere.",
    )
    parser.add_argument(
        "--tags",
        type=Path,
        default=TAGS_PACKAGE,
        help="package declaring the tag fragments",
    )
    parser.add_argument(
        "--reference-root",
        type=Path,
        action="append",
        dest="reference_roots",
        help="directory to count reads in, repeatable",
    )
    arguments = parser.parse_args(list(argv))

    tags: Path = arguments.tags
    reference_roots: Tuple[Path, ...] = tuple(arguments.reference_roots or REFERENCE_ROOTS)
    fragments = declared_fragments(discover_modules([tags]))
    counts = reference_counts(discover_modules(reference_roots))
    unread = unread_fragments(fragments, counts)
    if not unread:
        return 0

    print("Tag fragment(s) declared and never read:", file=sys.stderr)
    for name, location in unread:
        print(f"  {location}: {name}", file=sys.stderr)

    print(f"\nFound {len(unread)} unread tag fragment(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
