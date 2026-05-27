#!/usr/bin/env python3

import re
import sys
from pathlib import Path
from typing import Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
LOGIC_ROOT: Final[Path] = PROJECT_ROOT / "src" / "sampletones_application" / "logic"
DEARPYGUI_IMPORT_RE = re.compile(r"^\s*(import|from)\s+dearpygui\b")


def find_dearpygui_imports(filepath: Path) -> list[str]:
    violations = []
    for line_number, line in enumerate(filepath.read_text(encoding="utf-8").splitlines(), start=1):
        if DEARPYGUI_IMPORT_RE.match(line):
            violations.append(f"{filepath}:{line_number}: {line.strip()}")

    return violations


def main() -> None:
    logic_filepaths = [
        Path(argument).resolve() for argument in sys.argv[1:] if Path(argument).resolve().is_relative_to(LOGIC_ROOT)
    ]

    all_violations = [violation for filepath in logic_filepaths for violation in find_dearpygui_imports(filepath)]

    if all_violations:
        print("dearpygui import(s) found in logic/ — boundary violation:", file=sys.stderr)
        for violation in all_violations:
            print(f"  {violation}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
