#!/usr/bin/env python3

"""
Checks that every tag constant is named after the tag it composes.

`TAG_GLOBAL_WINDOW_MAIN = TagName(Page.GLOBAL, Panel.IMPLICIT, Widget.WINDOW, "main")` composes the
tag `global.window.main`, so its name is that tag upper-cased with each separator turned into an
underscore, behind the `TAG_` prefix. Reading the name therefore states the tag, and reading the tag
states where its constant lives.

Usage:
    python check_tag_names.py [files...]   # check the given modules
    python check_tag_names.py --all        # check every module of the tags package
"""

import argparse
import ast
import sys
from enum import StrEnum
from pathlib import Path
from typing import Dict, Final, List, NamedTuple, Optional, Sequence, Tuple, Type, TypeVar

from sampletones_application.categories.hierarchy import Page, Panel, Widget
from sampletones_application.categories.key.tag import TagName
from sampletones_application.tags.compose import TAG_SEPARATOR
from sampletones_shared.meta.source.constants import ModuleConstant, module_constants
from sampletones_shared.meta.source.modules import SourceModule, discover_modules, parse_module
from sampletones_shared.meta.source.nodes import terminal_name
from sampletones_shared.paths import REPOSITORY_ROOT

TAGS_PACKAGE: Final[Path] = REPOSITORY_ROOT / "src" / "sampletones_application" / "tags"

TAG_PREFIX: Final[str] = "TAG"
TAG_NAME_CLASS: Final[str] = "TagName"

PAGE_ARGUMENT: Final[str] = "page"
PANEL_ARGUMENT: Final[str] = "panel"
WIDGET_ARGUMENT: Final[str] = "widget"
ELEMENT_ARGUMENT: Final[str] = "element"
TAG_ARGUMENTS: Final[Tuple[str, ...]] = (PAGE_ARGUMENT, PANEL_ARGUMENT, WIDGET_ARGUMENT, ELEMENT_ARGUMENT)

EnumMember = TypeVar("EnumMember", bound=StrEnum)


class TagFinding(NamedTuple):
    """One tag constant the check reports, and what it reports about it."""

    location: str
    message: str


def expected_name(tag: TagName) -> str:
    """The constant name a tag calls for.

    Args:
        tag: Tag the constant composes.

    Returns:
        str: The name, such as `TAG_GLOBAL_WINDOW_MAIN`.
    """
    return f"{TAG_PREFIX}_{str(tag).upper().replace(TAG_SEPARATOR, '_')}"


def tag_call(constant: ModuleConstant) -> Optional[ast.Call]:
    """The `TagName(...)` call a constant is bound to, where it is bound to one."""
    value = constant.value
    if isinstance(value, ast.Call) and terminal_name(value.func) == TAG_NAME_CLASS:
        return value

    return None


def call_arguments(call: ast.Call) -> Optional[Dict[str, ast.expr]]:
    """The arguments a tag call passes, keyed by the parameter each one fills.

    Args:
        call: Call to read, written with positional arguments, keywords, or both.

    Returns:
        Optional[Dict[str, ast.expr]]: One entry per tag argument, or `None` where the call fills
            them in a form the check reads no arguments from.
    """
    arguments = dict(zip(TAG_ARGUMENTS, call.args, strict=False))
    for keyword in call.keywords:
        if keyword.arg is None:
            return None

        arguments[keyword.arg] = keyword.value

    if set(arguments) != set(TAG_ARGUMENTS):
        return None

    return arguments


def hierarchy_member(node: ast.expr, enum: Type[EnumMember]) -> Optional[EnumMember]:
    """The hierarchy member an argument names, such as `Page.GLOBAL`.

    Args:
        node: Argument to read.
        enum: Hierarchy enum the argument names a member of.

    Returns:
        Optional[EnumMember]: The member, or `None` where the argument names none.
    """
    match node:
        case ast.Attribute(value=ast.Name(id=owner), attr=member) if owner == enum.__name__:
            return enum.__members__.get(member)
        case _:
            return None


def element_name(node: ast.expr) -> Optional[str]:
    """The element an argument spells, where it spells one as a string literal."""
    match node:
        case ast.Constant(value=str() as element):
            return element
        case _:
            return None


def composed_tag(arguments: Dict[str, ast.expr]) -> Optional[TagName]:
    """The tag a set of arguments composes, where each one states its part.

    Args:
        arguments: Arguments of a tag call, as `call_arguments` keys them.

    Returns:
        Optional[TagName]: The composed tag, or `None` where an argument states something the check
            reads no part from.
    """
    page = hierarchy_member(arguments[PAGE_ARGUMENT], Page)
    panel = hierarchy_member(arguments[PANEL_ARGUMENT], Panel)
    widget = hierarchy_member(arguments[WIDGET_ARGUMENT], Widget)
    element = element_name(arguments[ELEMENT_ARGUMENT])
    if page is None or panel is None or widget is None or element is None:
        return None

    return TagName(page, panel, widget, element)


def check_constant(module: SourceModule, constant: ModuleConstant) -> Optional[TagFinding]:
    """Checks one constant of a tags module, where it is bound to a tag.

    Args:
        module: Module the constant lives in.
        constant: Constant to check.

    Returns:
        Optional[TagFinding]: What the check reports, or `None` where the constant is well named or
            holds no tag.
    """
    call = tag_call(constant)
    if call is None:
        return None

    location = f"{module.path}:{constant.line}"
    arguments = call_arguments(call)
    if arguments is None:
        return TagFinding(
            location=location,
            message=(
                f"{constant.name} calls {TAG_NAME_CLASS} in a form the check reads no arguments from; "
                f"a tag states {', '.join(TAG_ARGUMENTS)}"
            ),
        )

    tag = composed_tag(arguments)
    if tag is None:
        return TagFinding(
            location=location,
            message=(
                f"{constant.name} states its parts in a form the check reads no tag from; a tag names a "
                f"{Page.__name__}, a {Panel.__name__}, and a {Widget.__name__} member, then spells its "
                "element as a string literal"
            ),
        )

    expected = expected_name(tag)
    if constant.name != expected:
        return TagFinding(
            location=location,
            message=f"{constant.name} composes the tag {str(tag)!r}, which calls for the name {expected}",
        )

    return None


def check_module(module: SourceModule) -> List[TagFinding]:
    """Checks every tag constant one module declares."""
    findings = (check_constant(module, constant) for constant in module_constants(module.tree))
    return [finding for finding in findings if finding is not None]


def check_modules(modules: Sequence[SourceModule]) -> List[TagFinding]:
    """Checks every tag constant the given modules declare, in the order they were read."""
    return [finding for module in modules for finding in check_module(module)]


def main(argv: Sequence[str]) -> int:
    """Report any tag constant whose name departs from the tag it composes."""
    parser = argparse.ArgumentParser(
        description="Check that tag constant names state the tags they compose.",
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
        help=f"check every module under {TAGS_PACKAGE.name}/ instead of named files",
    )
    arguments = parser.parse_args(list(argv))

    files: List[Path] = arguments.files
    modules = discover_modules([TAGS_PACKAGE]) if arguments.all else [parse_module(path) for path in files]
    findings = check_modules(modules)
    if not findings:
        return 0

    print("Tag name(s) departing from the tag they compose:", file=sys.stderr)
    for location, message in findings:
        print(f"  {location}: {message}", file=sys.stderr)

    print(f"\nFound {len(findings)} tag name(s) to fix.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
