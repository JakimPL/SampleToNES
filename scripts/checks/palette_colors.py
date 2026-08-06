#!/usr/bin/env python3

"""
Checks that a colour stays a palette token until the moment it is drawn with.

`PaletteColor.rgba` answers with the palette active right now, so a consumer that holds the
token follows a palette swap and one that stores the answer keeps the shade it read at
construction. The check reports the two ways that contract is lost: an attribute assigned the
resolved value, and a colour written into the shipped configuration as a literal instead of a
palette token.

Usage:
    python scripts/checks/palette_colors.py            # check the source tree and the config package
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Final, Iterator, List, NamedTuple, Sequence, Tuple

from sampletones_shared.meta.source.modules import SourceModule, discover_modules
from sampletones_shared.paths import REPOSITORY_ROOT

SOURCE_ROOT: Final[Path] = REPOSITORY_ROOT / "src"
APPLICATION_PACKAGE: Final[Path] = SOURCE_ROOT / "sampletones_application"
CONFIG_PACKAGE: Final[Path] = SOURCE_ROOT / "sampletones_config"
PALETTES_DIRECTORY: Final[Path] = CONFIG_PACKAGE / "palettes"

COLOR_PROPERTY: Final[str] = "rgba"
SELF_NAMES: Final[Tuple[str, ...]] = ("self", "cls")

CONFIG_PATTERN: Final[str] = "*.yaml"
HEX_COLOR: Final[re.Pattern[str]] = re.compile(r"[\"']#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?[\"']")


class ColorFinding(NamedTuple):
    """One place a colour stops following the palette, and what to do about it."""

    location: str
    message: str


def _assigned_targets(statement: ast.stmt) -> Tuple[ast.expr, ...]:
    if isinstance(statement, ast.Assign):
        return tuple(statement.targets)

    if isinstance(statement, ast.AnnAssign):
        return (statement.target,)

    return ()


def _is_own_attribute(target: ast.expr) -> bool:
    return isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in SELF_NAMES


def _resolves_a_color(value: ast.expr) -> bool:
    return isinstance(value, ast.Attribute) and value.attr == COLOR_PROPERTY


def stored_colors(module: SourceModule) -> Iterator[ColorFinding]:
    """Every attribute a module assigns the resolved value of a palette colour.

    Args:
        module: Module to read.

    Yields:
        ColorFinding: One per assignment, naming the attribute that keeps the stale shade.
    """
    for statement in ast.walk(module.tree):
        value = getattr(statement, "value", None)
        if value is None or not _resolves_a_color(value):
            continue

        if not isinstance(statement, ast.stmt):
            continue

        for target in _assigned_targets(statement):
            if _is_own_attribute(target):
                yield ColorFinding(
                    location=module.location(statement),
                    message=(
                        f"stores .{COLOR_PROPERTY}; hold the PaletteColor and read "
                        f".{COLOR_PROPERTY} where the colour reaches DearPyGui"
                    ),
                )


def literal_colors(path: Path) -> Iterator[ColorFinding]:
    """Every hex colour a shipped configuration file writes out in place of a palette token.

    Args:
        path: Configuration file to read.

    Yields:
        ColorFinding: One per literal, naming the line that holds it.
    """
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        for match in HEX_COLOR.finditer(line):
            yield ColorFinding(
                location=f"{path}:{number}",
                message=f"writes the colour {match.group()} directly; name a palette token instead",
            )


def find_stored_colors(package: Path) -> List[ColorFinding]:
    return [finding for module in discover_modules([package]) for finding in stored_colors(module)]


def find_literal_colors(package: Path, palettes: Path) -> List[ColorFinding]:
    return [
        finding
        for path in sorted(package.rglob(CONFIG_PATTERN))
        if palettes not in path.parents
        for finding in literal_colors(path)
    ]


def main(argv: Sequence[str]) -> int:
    """Report every colour the application stores resolved or the configuration writes out."""
    parser = argparse.ArgumentParser(
        description="Check that a colour stays a palette token until it is drawn with.",
    )
    parser.add_argument(
        "--package",
        type=Path,
        default=APPLICATION_PACKAGE,
        help="package whose colour reads to check",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=CONFIG_PACKAGE,
        help="shipped configuration package whose colours must name palette tokens",
    )
    parser.add_argument(
        "--palettes",
        type=Path,
        default=PALETTES_DIRECTORY,
        help="directory holding the palettes, where colour values belong",
    )
    arguments = parser.parse_args(list(argv))

    findings = find_stored_colors(arguments.package) + find_literal_colors(arguments.config, arguments.palettes)
    if not findings:
        return 0

    print("Colour(s) that stop following the active palette:", file=sys.stderr)
    for location, message in findings:
        print(f"  {location}: {message}", file=sys.stderr)

    print(f"\nFound {len(findings)} colour(s) detached from the palette.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
