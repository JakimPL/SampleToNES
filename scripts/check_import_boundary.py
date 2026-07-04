#!/usr/bin/env python3

"""
Enforces layer-boundary import rules across the sampletones_application package.

Each rule names a file glob, the import prefixes forbidden there, and the
contract modules exempt from those prefixes: a layer may consume another
layer's data contract (e.g. a service's result types) while its implementation
modules stay out of reach. The script checks every Python source file matched
by the glob and reports any import that begins with a forbidden prefix.

Usage:
    python check_import_boundary.py [files...]   # check specific files
    python check_import_boundary.py --all        # run all rules against the source tree
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

APP_ROOT = Path(__file__).parent.parent / "src" / "sampletones_application"

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
    forbidden: list[str]
    contracts: list[str] = []


RULES: list[BoundaryRule] = [
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
        "ui/**/*.py",
        [
            "sampletones_application.coordinators",
            "sampletones_application.logic",
            "sampletones_application.services",
            "sampletones_application.config",
            "sampletones_application.application",
            "sampletones_application.shell",
        ],
    ),
]


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + ".")


def find_violations(
    filepath: Path,
    rule: BoundaryRule,
) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
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
                violations.append((prefix, f"{location}: {line.strip()}"))
                break

    return violations


def run_all_rules() -> list[tuple[str, str]]:
    all_violations: list[tuple[str, str]] = []
    for rule in RULES:
        for filepath in sorted(APP_ROOT.glob(rule.pattern)):
            all_violations.extend(find_violations(filepath, rule))

    return all_violations


def run_on_files(filepaths: list[Path]) -> list[tuple[str, str]]:
    all_violations: list[tuple[str, str]] = []
    for rule in RULES:
        matched = {path for path in filepaths if path.match(rule.pattern)}
        for filepath in sorted(matched):
            all_violations.extend(find_violations(filepath, rule))

    return all_violations


def main() -> None:
    args = sys.argv[1:]

    if args == ["--all"]:
        all_violations = run_all_rules()
    else:
        filepaths = [Path(argument) for argument in args]
        all_violations = run_on_files(filepaths)

    if all_violations:
        print("Layer boundary violation(s) found:", file=sys.stderr)
        for kind, location in all_violations:
            print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
