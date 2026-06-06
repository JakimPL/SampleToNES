#!/usr/bin/env python3
"""
Checks for cross-object private member access in coordinator and application code.

Accessing a private attribute of another object (e.g. ``obj._method``) breaks
encapsulation across coordinator boundaries. Only ``self._x`` and ``cls._x``
are permitted.

Usage:
    python check_private_access.py [files...]   # check specific files
    python check_private_access.py --all        # check application.py + coordinators/
"""

import re
import sys
from pathlib import Path

APP_ROOT = Path(__file__).parent.parent / "src" / "sampletones_application"

CHECKED_PATHS = [
    APP_ROOT / "application.py",
    APP_ROOT / "coordinators",
]

# Matches <identifier>._<attr> where identifier is not "self" or "cls".
# Covers attribute access and keyword-argument values (e.g. foo=bar._baz).
_PRIVATE_ACCESS_RE = re.compile(r"\b(?!self\b)(?!cls\b)[a-zA-Z_]\w*\._[a-z_]")

# Lines starting with a comment or containing only a string literal are skipped.
_COMMENT_LINE_RE = re.compile(r"^\s*#")
_DOCSTRING_BOUNDARY_RE = re.compile(r'^\s*"""')


def find_violations(filepath: Path) -> list[tuple[int, str]]:
    violations: list[tuple[int, str]] = []
    in_docstring = False
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if _DOCSTRING_BOUNDARY_RE.match(line):
            occurrences = stripped.count('"""')
            if occurrences == 1:
                in_docstring = not in_docstring
            continue
        if in_docstring or _COMMENT_LINE_RE.match(line):
            continue
        if _PRIVATE_ACCESS_RE.search(line):
            violations.append((line_number, line.rstrip()))
    return violations


def collect_files(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    for path in paths:
        if path.is_dir():
            result.extend(sorted(path.glob("**/*.py")))
        elif path.is_file():
            result.append(path)
    return result


def main() -> None:
    args = sys.argv[1:]

    if args == ["--all"]:
        filepaths = collect_files(CHECKED_PATHS)
    else:
        filepaths = [Path(argument) for argument in args]

    found_any = False
    for filepath in filepaths:
        violations = find_violations(filepath)
        if violations:
            found_any = True
            for line_number, line in violations:
                print(f"{filepath}:{line_number}: {line.strip()}", file=sys.stderr)

    if found_any:
        print(
            "\ncross-object private access detected — expose a public API instead",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
