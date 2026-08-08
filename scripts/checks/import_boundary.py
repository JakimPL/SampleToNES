#!/usr/bin/env python3

"""
Enforces layer-boundary import rules across the sampletones_application package.

Each import rule names a file glob, the import prefixes forbidden there, and the
contract modules exempt from those prefixes: a layer may consume another
layer's data contract (e.g. a service's result types) while its implementation
modules stay out of reach. The script checks every Python source file matched
by the glob and reports any import that begins with a forbidden prefix.

Token rules additionally forbid a regex within a file glob, enforcing contracts
a prefix cannot express — e.g. that panels never compose a column suffix
(`SUF_PANEL_*`) or parent into another panel's container.

Usage:
    python scripts/checks/import_boundary.py [files...]   # check specific files
    python scripts/checks/import_boundary.py --all        # run all rules against the source tree
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Final, List, NamedTuple, Optional, Sequence, Set

from sampletones_shared.meta.source.modules import source_paths
from sampletones_shared.meta.source.packages import package_directory

APP_ROOT: Final[Path] = package_directory("sampletones_application")

IMPORT_RE = re.compile(r"^\s*(import|from)\s+([\w.]+)")

VISUAL = [
    "dearpygui",
    "sampletones_application.ui",
    "sampletones_application.utils.gui",
]

SERVICE_CONTRACTS = [
    "sampletones_application.services.result",
    "sampletones_application.services.song_player.result",
]


class BoundaryRule(NamedTuple):
    pattern: str
    forbidden: List[str]
    contracts: List[str] = []


class TokenRule(NamedTuple):
    pattern: str
    forbidden: str
    message: str


class Violation(NamedTuple):
    """One import or token a rule forbids, and where a reader opens it."""

    kind: str
    location: str


RULES: List[BoundaryRule] = [
    BoundaryRule(
        "config/**/*.py",
        [
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.application",
        ],
    ),
    BoundaryRule(
        "logic/**/*.py",
        [
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.services",
        ],
        contracts=SERVICE_CONTRACTS,
    ),
    BoundaryRule(
        "view_model/**/*.py",
        [
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
            "sampletones_application.services",
        ],
    ),
    BoundaryRule(
        "services/**/*.py",
        [
            *VISUAL,
            "sampletones_application.view_model",
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
        ],
    ),
    BoundaryRule(
        "shell.py",
        [
            "sampletones_application.logic",
            "sampletones_application.services",
        ],
    ),
    BoundaryRule(
        "coordinators/**/*.py",
        [
            "sampletones_application.application",
            "sampletones_application.shell",
        ],
    ),
    BoundaryRule(
        "ui/**/*.py",
        [
            "sampletones_application.coordinators",
            "sampletones_application.logic",
            "sampletones_application.services",
            "sampletones_application.config",
            "sampletones_application.application",
            "sampletones_application.shell",
            "sampletones_application.utils.gui.dialogs",
        ],
    ),
]


TOKEN_RULES: List[TokenRule] = [
    TokenRule(
        "ui/panels/**/*.py",
        r"\bSUF_PANEL_",
        "ui/panels must not reference a column suffix (SUF_PANEL_*); a panel receives its "
        "parent through create_panel(parent), set by the coordinator that owns the layout",
    ),
    TokenRule(
        "ui/panels/**/*.py",
        r"parent\s*=\s*TAG_SEQUENCER_GRID_PANEL\b",
        "ui/panels must not parent into another panel's container (TAG_SEQUENCER_GRID_PANEL); "
        "the coordinator injects the parent through create_panel(parent)",
    ),
    TokenRule(
        "ui/panels/**/*.py",
        r"\bTAG_GLOBAL_THEME_PANEL_(SURFACE|GROUND)\b",
        "ui/panels must not bind a structural depth theme (TAG_GLOBAL_THEME_PANEL_SURFACE/"
        "GROUND); only the layout primitives own depth (TabColumns binds the column, card() "
        "binds the card), and a panel binds only semantic themes",
    ),
]


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def find_token_violations(
    filepath: Path,
    rule: TokenRule,
) -> List[Violation]:
    pattern = re.compile(rule.forbidden)
    violations: List[Violation] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if pattern.search(line):
            location = f"{filepath}:{line_number}"
            violations.append(
                Violation(
                    kind=rule.message,
                    location=f"{location}: {line.strip()}",
                )
            )

    return violations


def find_violations(
    filepath: Path,
    rule: BoundaryRule,
) -> List[Violation]:
    violations: List[Violation] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        match = IMPORT_RE.match(line)
        if match is None:
            continue

        module = match.group(2)
        if any(_matches_prefix(module, contract) for contract in rule.contracts):
            continue

        for prefix in rule.forbidden:
            if _matches_prefix(module, prefix):
                location = f"{filepath}:{line_number}"
                violations.append(
                    Violation(
                        kind=prefix,
                        location=f"{location}: {line.strip()}",
                    )
                )
                break

    return violations


def rule_modules(
    package: Path,
    pattern: str,
    swept: Set[Path],
    selection: Optional[Set[Path]],
) -> List[Path]:
    """The modules a rule reaches, in path order.

    A rule names its files by one glob whether the check runs over the whole package or over the
    files a hook lists, so the two entry points read the same rule the same way.

    Args:
        package: Package the rule globs are written against.
        pattern: Glob the rule names its files by.
        swept: Visible modules the package holds, which the glob is held to.
        selection: Resolved paths to narrow the rule to, or `None` to reach every module it names.

    Returns:
        List[Path]: The modules the rule applies to.
    """
    matched = {path.resolve() for path in package.glob(pattern)} & swept
    if selection is not None:
        matched &= selection

    return sorted(matched)


def check_boundaries(package: Path, selection: Optional[Set[Path]]) -> List[Violation]:
    """Every import and token the rules forbid in the package.

    The package is swept first, so the rules run over the modules it holds and a root reading as
    empty stops the check where it would otherwise report a clean tree.

    Args:
        package: Package the rule globs are written against.
        selection: Resolved paths to narrow the check to, or `None` to check the whole package.

    Returns:
        List[Violation]: What the rules report, boundary rules first.

    Raises:
        NotADirectoryError: If the package names no directory.
        FileNotFoundError: If the package holds no module to read.
    """
    swept = {path.resolve() for path in source_paths([package])}
    violations = [
        violation
        for rule in RULES
        for filepath in rule_modules(package, rule.pattern, swept, selection)
        for violation in find_violations(filepath, rule)
    ]
    violations.extend(
        violation
        for token_rule in TOKEN_RULES
        for filepath in rule_modules(package, token_rule.pattern, swept, selection)
        for violation in find_token_violations(filepath, token_rule)
    )
    return violations


def main(argv: Sequence[str]) -> int:
    """Report every import and token the layer boundaries forbid."""
    parser = argparse.ArgumentParser(
        description="Check layer-boundary import rules across the application package.",
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
        help=f"check every module under {APP_ROOT.name}/ instead of named files",
    )
    parser.add_argument(
        "--package",
        type=Path,
        default=APP_ROOT,
        help="package the rule globs are written against",
    )
    arguments = parser.parse_args(list(argv))

    files: List[Path] = arguments.files
    selection = None if arguments.all else {path.resolve() for path in files}
    violations = check_boundaries(arguments.package, selection)
    if not violations:
        return 0

    print("Layer boundary violation(s) found:", file=sys.stderr)
    for kind, location in violations:
        print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

    print(f"\nFound {len(violations)} violation(s) in total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
