#!/usr/bin/env python3

"""
Enforces layer-boundary import rules across the sampletones_application package.

Each rule is a (glob_pattern, forbidden_prefixes) pair. The script checks every
Python source file matched by the glob and reports any import that begins with
one of the forbidden prefixes.

Usage:
    python check_import_boundary.py [files...]   # check specific files
    python check_import_boundary.py --all        # run all rules against the source tree
"""

import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent / "src" / "sampletones_application"

IMPORT_RE = re.compile(r"^\s*(import|from)\s+([\w.]+)")

RULES: list[tuple[str, list[str]]] = [
    (
        "logic/**/*.py",
        [
            "dearpygui",
            "sampletones_application.ui",
            "sampletones_application.coordinators",
        ],
    ),
    (
        "view_model/**/*.py",
        [
            "dearpygui",
            "sampletones_application.ui",
            "sampletones_application.coordinators",
            "sampletones_application.logic",
            "sampletones_application.services",
        ],
    ),
    (
        "services/**/*.py",
        [
            "dearpygui",
            "sampletones_application.ui",
            "sampletones_application.view_model",
            "sampletones_application.coordinators",
            "sampletones_application.logic",
        ],
    ),
    (
        "shell.py",
        [
            "sampletones_application.logic",
            "sampletones_application.services",
        ],
    ),
]


def find_violations(filepath: Path, forbidden_prefixes: list[str]) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        match = IMPORT_RE.match(line)
        if match is None:
            continue

        module = match.group(2)
        for prefix in forbidden_prefixes:
            if module == prefix or module.startswith(prefix + "."):
                location = f"{filepath}:{line_number}"
                violations.append((prefix, f"{location}: {line.strip()}"))
                break

    return violations


def run_all_rules() -> list[tuple[str, str]]:
    all_violations: list[tuple[str, str]] = []
    for glob_pattern, forbidden_prefixes in RULES:
        for filepath in sorted(APP_ROOT.glob(glob_pattern)):
            all_violations.extend(find_violations(filepath, forbidden_prefixes))

    return all_violations


def run_on_files(filepaths: list[Path]) -> list[tuple[str, str]]:
    all_violations: list[tuple[str, str]] = []
    for rule_glob, forbidden_prefixes in RULES:
        matched = {path for path in filepaths if path.match(rule_glob)}
        for filepath in sorted(matched):
            all_violations.extend(find_violations(filepath, forbidden_prefixes))

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
