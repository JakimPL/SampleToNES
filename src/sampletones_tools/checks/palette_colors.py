import ast
import logging
import re
import sys
from collections.abc import Iterator, Sequence
from itertools import chain
from pathlib import Path
from typing import Final, List, NamedTuple, Tuple, Union

from sampletones_shared.logger import logger
from sampletones_tools.checks.source.modules import SourceModule, discover_modules
from sampletones_tools.checks.source.nodes import terminal_name
from sampletones_tools.checks.source.packages import source_package_directory

APPLICATION_PACKAGE: Final[Path] = source_package_directory("sampletones_application")

HEX_COLOR: Final[re.Pattern[str]] = re.compile(r"[\"']#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?[\"']")

COLOR_PROPERTY: Final[str] = "rgba"
SELF_NAMES: Final[Tuple[str, ...]] = ("self", "cls")

THEME_COLOR_CALL: Final[str] = "add_theme_color"
CONFIG_PATTERN: Final[str] = "*.yaml"


Assignment = Union[ast.Assign, ast.AnnAssign]


class ColorFinding(NamedTuple):
    """One place a color stops following the palette, and what to do about it."""

    location: str
    message: str


def _assignments(tree: ast.Module) -> Iterator[Assignment]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            yield node


def _assigned_targets(statement: Assignment) -> Tuple[ast.expr, ...]:
    if isinstance(statement, ast.Assign):
        return tuple(statement.targets)

    return (statement.target,)


def _is_own_attribute(target: ast.expr) -> bool:
    return isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id in SELF_NAMES


def _resolves_a_color(value: ast.expr) -> bool:
    return isinstance(value, ast.Attribute) and value.attr == COLOR_PROPERTY


def stored_colors(module: SourceModule) -> Iterator[ColorFinding]:
    """Every attribute a module assigns the resolved value of a palette color.

    Args:
        module: Module to read.

    Yields:
        ColorFinding: One per assignment, naming the attribute that keeps the stale shade.
    """
    for statement in _assignments(module.tree):
        if statement.value is None or not _resolves_a_color(statement.value):
            continue

        for target in _assigned_targets(statement):
            if _is_own_attribute(target):
                yield ColorFinding(
                    location=module.location(statement),
                    message=(
                        f"stores .{COLOR_PROPERTY}; hold the BaseColor and read "
                        f".{COLOR_PROPERTY} where the color reaches DearPyGui"
                    ),
                )


def dpg_module_helper() -> Tuple[Path, str]:
    """The module allowed to fill a theme color, and the helper every other module calls.

    Returns:
        Tuple[Path, str]: The resolved path of the bindings module, and the helper's name.
    """
    import sampletones_application.utils.gui.palette.dpg as bindings

    return Path(bindings.__file__).resolve(), bindings.dpg_add_palette_theme_color.__name__


def unregistered_theme_colors(
    module: SourceModule,
    *,
    bindings_module: Path,
    theme_color_helper: str,
) -> Iterator[ColorFinding]:
    """Every theme color a module fills without recording the token behind it.

    Args:
        module: Module to read.
        bindings_module: Module the call belongs in, which records the token in the same breath.
        theme_color_helper: Name of the helper a report points at.

    Yields:
        ColorFinding: One per call, naming the theme color that stays at the shade it was
            built with.
    """
    if module.path.resolve() == bindings_module:
        return

    for node in ast.walk(module.tree):
        if isinstance(node, ast.Call) and terminal_name(node.func) == THEME_COLOR_CALL:
            yield ColorFinding(
                location=module.location(node),
                message=f"fills a theme color directly; call {theme_color_helper} so a swap repaints it",
            )


def literal_colors(path: Path) -> Iterator[ColorFinding]:
    """Every hex color a shipped configuration file writes out in place of a palette token.

    Args:
        path: Configuration file to read.

    Yields:
        ColorFinding: One per literal, naming the line that holds it.
    """
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        for match in HEX_COLOR.finditer(line):
            yield ColorFinding(
                location=f"{path}:{number}",
                message=f"writes the color {match.group()} directly; name a palette token instead",
            )


def find_detached_colors(
    package: Path,
    *,
    bindings_module: Path,
    theme_color_helper: str,
) -> List[ColorFinding]:
    return [
        finding
        for module in discover_modules([package])
        for finding in chain(
            stored_colors(module),
            unregistered_theme_colors(
                module,
                bindings_module=bindings_module,
                theme_color_helper=theme_color_helper,
            ),
        )
    ]


def find_literal_colors(package: Path, palettes: Path) -> List[ColorFinding]:
    """Every hex color the shipped configuration writes out, outside the palettes that carry values.

    Args:
        package: Configuration package to sweep.
        palettes: Directory holding the palettes, where a color value belongs.

    Returns:
        List[ColorFinding]: One finding per literal, in file order.

    Raises:
        FileNotFoundError: If the package holds no configuration file to read.
    """
    paths = sorted(package.rglob(CONFIG_PATTERN))
    if not paths:
        raise FileNotFoundError(f"The configuration package {package} holds no {CONFIG_PATTERN} file to read")

    return [finding for path in paths if palettes not in path.parents for finding in literal_colors(path)]


def check_colors(package: Path, config: Path, palettes: Path) -> List[ColorFinding]:
    """Every color the application stores resolved or the configuration writes out.

    Args:
        package: Package whose color reads are checked.
        config: Shipped configuration package whose colors must name palette tokens.
        palettes: Directory holding the palettes, where color values belong.

    Returns:
        List[ColorFinding]: The detached colors of the package, then the literal colors of the
            configuration.
    """
    logger.set_level(level=logging.ERROR)
    bindings_module, theme_color_helper = dpg_module_helper()
    findings = find_detached_colors(
        package,
        bindings_module=bindings_module,
        theme_color_helper=theme_color_helper,
    )
    findings.extend(find_literal_colors(config, palettes))
    return findings


def report(findings: Sequence[ColorFinding]) -> int:
    """Prints every finding on the standard error stream and answers with the exit status."""
    if not findings:
        return 0

    print("Color(s) that stop following the active palette:", file=sys.stderr)
    for location, message in findings:
        print(f"  {location}: {message}", file=sys.stderr)

    print(
        f"\nFound {len(findings)} color(s) detached from the palette.",
        file=sys.stderr,
    )
    return 1
