#!/usr/bin/env python3

"""
Enforces the import boundaries the source tree is layered by.

A layer graph names a tree of modules, the units it divides into, and the units each one may
import; every other unit is out of reach, so an edge across the graph is declared before it is
taken. The packages under `src/` are one such graph — `sampletones_core` sits below
`sampletones_player`, which is what keeps the reconstruction engine clear of the console player —
and the player's own subpackages are another, where `driver/assembler/` reaches the cc65 toolchain
and stays outside the wheel, so no shipped module imports it.

Boundary rules state a contract the other way round, by the import prefixes a directory stays clear
of, and carry the contract modules exempt from those prefixes: a layer may consume another layer's
data contract (e.g. a service's result types) while its implementation modules stay out of reach.
`sampletones_application` is layered that way.

Token rules additionally forbid a regex within a file glob, enforcing contracts a prefix cannot
express — e.g. that panels never compose a column suffix (`SUF_PANEL_*`) or parent into another
panel's container.

`sampletones_config/boundaries/` declares what the boundaries are and
`sampletones_shared/meta/import_boundary/` holds how they are read and reported; this script runs
them over a source tree and prints what they find.

Usage:
    python scripts/checks/import_boundary.py [files...]   # check specific files
    python scripts/checks/import_boundary.py --all        # run all rules against the source tree
"""

import argparse
import sys
from pathlib import Path
from typing import List, Sequence

from sampletones_shared.meta.import_boundary.check import check_boundaries
from sampletones_shared.meta.import_boundary.configs.rules import ImportBoundaryRules
from sampletones_shared.paths.source import SOURCE_ROOT


def main(argv: Sequence[str]) -> int:
    """Report every import and token the layer boundaries forbid."""
    parser = argparse.ArgumentParser(
        description="Check the import boundaries the source tree is layered by.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        help="modules to check",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=f"check every module under {SOURCE_ROOT.name}/ instead of named files",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_ROOT,
        help="source root the rule roots are named within",
    )
    arguments = parser.parse_args(list(argv))

    files: List[Path] = arguments.files
    selection = None if arguments.all else {path.resolve() for path in files}
    boundaries = ImportBoundaryRules.load()
    violations = check_boundaries(
        arguments.source,
        boundaries.boundary_rules(),
        boundaries.tokens,
        selection,
    )
    if not violations:
        return 0

    print("Layer boundary violation(s) found:", file=sys.stderr)
    for kind, location in violations:
        print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

    print(f"\nFound {len(violations)} violation(s) in total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
