#!/usr/bin/env python3

"""
Checks that no case holds text it rendered itself against a literal it spelled out.

Rendering a value and comparing the result with a written-out string pins whatever decided that
rendering. `str(path)` reads one way on Windows and another elsewhere, and a formatted setting reads
whatever the build ships, so a case written that way passes where it was authored and fails where it
is run next. Comparing the values instead — a `Path` against a `Path`, a setting against the
configuration it comes from — holds on every platform and survives every tuning.

Equality is what pins a rendering entire, so that is what the check reads; a case holding a
fragment picks one clear of anything a platform decides. Every hit therefore reads under one of two
rules in `guidelines.md`: a case assumes no one platform, or a shipped value is a choice rather than
a contract.

Usage:
    python scripts/checks/rendered_literals.py
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Final, Iterator, List, NamedTuple, Sequence, Tuple, Type

from sampletones_shared.meta.source.modules import SourceModule, discover_modules
from sampletones_shared.paths.source import REPOSITORY_ROOT

TEST_ROOTS: Final[Tuple[Path, ...]] = (REPOSITORY_ROOT / "tests",)

EQUALITY_OPERATORS: Final[Tuple[Type[ast.cmpop], ...]] = (ast.Eq, ast.NotEq)
RENDERING_CALL: Final[str] = "str"
CALL_RENDERING: Final[str] = "str()"
TEMPLATE_RENDERING: Final[str] = "an f-string"


class Finding(NamedTuple):
    """One comparison holding rendered text against a spelled-out literal."""

    location: str
    rendering: str


def rendering_of(node: ast.expr) -> str:
    """How an expression turns a value into text, where it does.

    Args:
        node: Expression to read.

    Returns:
        str: The rendering's name, or an empty string where the expression renders nothing.
    """
    match node:
        case ast.Call(func=ast.Name(id=called)) if called == RENDERING_CALL:
            return CALL_RENDERING
        case ast.JoinedStr(values=values) if any(isinstance(value, ast.FormattedValue) for value in values):
            return TEMPLATE_RENDERING
        case _:
            return ""


def spells_text(node: ast.expr) -> bool:
    """Whether an expression is a string written out in the case itself."""
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def states_equality(node: ast.Compare) -> bool:
    """Whether a comparison asks for the whole of one side to read as the other.

    Equality is what pins a rendering entire. Containment holds a fragment the case picked, which
    it can pick clear of anything a platform decides, so those are left to the case.
    """
    return all(isinstance(operator, EQUALITY_OPERATORS) for operator in node.ops)


def comparison_finding(module: SourceModule, node: ast.Compare) -> List[Finding]:
    """The finding a comparison earns, where one side renders text and another spells it out.

    Args:
        module: Module the comparison sits in.
        node: Comparison to read.

    Returns:
        List[Finding]: The finding, or an empty list where the comparison holds values.
    """
    if not states_equality(node):
        return []

    sides = [node.left, *node.comparators]
    renderings = tuple(filter(None, (rendering_of(side) for side in sides)))
    if not renderings or not any(spells_text(side) for side in sides):
        return []

    return [Finding(location=module.location(node), rendering=renderings[0])]


def module_findings(module: SourceModule) -> Iterator[Finding]:
    """Every comparison in a module that holds rendered text against a spelled-out literal."""
    for node in ast.walk(module.tree):
        if isinstance(node, ast.Compare):
            yield from comparison_finding(module, node)


def findings(modules: Sequence[SourceModule]) -> List[Finding]:
    """Every such comparison across the given modules, in the order they were read."""
    return [finding for module in modules for finding in module_findings(module)]


def main(argv: Sequence[str]) -> int:
    """Report every case comparing text it rendered with a literal it spelled out."""
    parser = argparse.ArgumentParser(
        description="Check that no case holds rendered text against a spelled-out literal.",
    )
    parser.add_argument(
        "--tests",
        type=Path,
        action="append",
        dest="roots",
        help="directory of cases to read, repeatable",
    )
    arguments = parser.parse_args(list(argv))

    roots: Tuple[Path, ...] = tuple(arguments.roots or TEST_ROOTS)
    found = findings(discover_modules(roots))
    if not found:
        return 0

    print("Case(s) holding rendered text against a spelled-out literal:", file=sys.stderr)
    for location, rendering in found:
        print(f"  {location}: {rendering} compared with a written-out string", file=sys.stderr)

    print(
        f"\nFound {len(found)} such comparison(s). Compare the values rather than their text: "
        "a Path against a Path, a configured value against the configuration it comes from.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
