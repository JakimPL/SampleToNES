import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Final, List, NamedTuple, Sequence, Tuple

from sampletones_shared.paths.source import REPOSITORY_ROOT, SCRIPTS_ROOT, SOURCE_ROOT
from sampletones_tools.checks.source.constants import module_constants
from sampletones_tools.checks.source.modules import SourceModule, discover_modules
from sampletones_tools.checks.source.packages import package_directory
from sampletones_tools.checks.source.references import count_identifier_loads

TAGS_PACKAGE: Final[Path] = package_directory("sampletones_application", "tags")
REFERENCE_ROOTS: Final[Tuple[Path, ...]] = (
    SOURCE_ROOT,
    REPOSITORY_ROOT / "tests",
    SCRIPTS_ROOT,
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


def check_reads(tags: Path, reference_roots: Sequence[Path]) -> List[Fragment]:
    """Every tag fragment the package declares and the reference roots never read."""
    fragments = declared_fragments(discover_modules([tags]))
    counts = reference_counts(discover_modules(reference_roots))
    return unread_fragments(fragments, counts)


def report(unread: Sequence[Fragment]) -> int:
    """Prints every unread fragment on the standard error stream and answers with the exit status."""
    if not unread:
        return 0

    print("Tag fragment(s) declared and never read:", file=sys.stderr)
    for name, location in unread:
        print(f"  {location}: {name}", file=sys.stderr)

    print(f"\nFound {len(unread)} unread tag fragment(s).", file=sys.stderr)
    return 1
