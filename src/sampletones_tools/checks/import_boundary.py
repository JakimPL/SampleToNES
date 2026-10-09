import sys
from pathlib import Path
from typing import List, Optional, Sequence, Set

from sampletones_tools.checks.boundary.check import check_boundaries
from sampletones_tools.checks.boundary.configs.rules import ImportBoundaryRules
from sampletones_tools.checks.boundary.packages import check_packages
from sampletones_tools.checks.boundary.standalone import check_standalone
from sampletones_tools.checks.boundary.violation import Violation


def check_imports(
    source: Path,
    scripts: Path,
    checkout: Path,
    selection: Optional[Set[Path]],
) -> List[Violation]:
    """Every import, token and namespace package the shipped boundaries forbid under the three trees.

    Args:
        source: Source root the rule roots are named within.
        scripts: Scripts tree the standalone rules are written against.
        checkout: Repository root the units beside the source tree are named within.
        selection: Resolved paths to narrow the check to, or `None` to check the trees whole.

    Returns:
        List[Violation]: What the rules report: the source tree's, then the checkout units', then
            the scripts tree's.
    """
    boundaries = ImportBoundaryRules.load()
    return [
        *check_boundaries(source, boundaries.boundary_rules(), boundaries.tokens, selection),
        *check_packages(source, selection),
        *check_boundaries(checkout, boundaries.checkout_rules(), (), selection),
        *(violation for unit in boundaries.checkout_units for violation in check_packages(checkout / unit, selection)),
        *check_standalone(scripts, boundaries.standalone, selection),
    ]


def report(violations: Sequence[Violation]) -> int:
    """Prints every violation on the standard error stream and answers with the exit status."""
    if not violations:
        return 0

    print("Layer boundary violation(s) found:", file=sys.stderr)
    for kind, location in violations:
        print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

    print(f"\nFound {len(violations)} violation(s) in total.", file=sys.stderr)
    return 1
