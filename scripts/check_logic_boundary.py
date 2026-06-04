#!/usr/bin/env python3

import re
import sys
from pathlib import Path

DEARPYGUI_IMPORT_RE = re.compile(r"^\s*(import|from)\s+dearpygui\b")
UI_IMPORT_RE = re.compile(r"^\s*(import|from)\s+sampletones_application\.ui\b")


def find_violations(filepath: Path) -> list[tuple[str, str]]:
    violations: list[tuple[str, str]] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        location = f"{filepath}:{line_number}"
        if DEARPYGUI_IMPORT_RE.match(line):
            violations.append(
                ("dearpygui import", f"{location}: {line.strip()}"),
            )
        elif UI_IMPORT_RE.match(line):
            violations.append(
                ("ui layer import", f"{location}: {line.strip()}"),
            )

    return violations


def main() -> None:
    filepaths = [Path(argument) for argument in sys.argv[1:]]

    all_violations = [violation for filepath in filepaths for violation in find_violations(filepath)]

    if all_violations:
        print(
            "boundary violation(s) found in logic/view_model:",
            file=sys.stderr,
        )
        for kind, location in all_violations:
            print(f"  [{kind}] {location}", file=sys.stderr)

        sys.exit(1)


if __name__ == "__main__":
    main()
