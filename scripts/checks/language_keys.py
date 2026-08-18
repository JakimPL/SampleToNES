#!/usr/bin/env python3

"""
Checks the language file and the lookups that read it against each other, in both directions.

Every lookup on a `LanguageManager` states a key, so the check reads each one and holds it against
`en.yaml`. A key spelled entirely from literals must name an entry, and every entry must be reachable
from some lookup — a key part arriving in a variable stands for each member of the enum it is
annotated with, which is why a dynamic part names a concrete element enum. An element enum is found
by what it derives from, so one lives wherever its domain lives and the check reads it there.

Three things are reported:
    broken lookup      — a literal key the language file holds no entry for
    unresolved part    — a key part the check reads no values from
    unreached entry    — an entry no lookup asks for

Usage:
    python scripts/checks/language_keys.py
"""

import argparse
import importlib
import inspect
import sys
from enum import Enum, EnumMeta
from pathlib import Path
from types import ModuleType
from typing import Callable, Dict, Final, List, Mapping, NamedTuple, Optional, Sequence, Type

import yaml

from sampletones_application.categories import hierarchy
from sampletones_application.categories.abstract import AbstractElement
from sampletones_application.paths import LANG_EN
from sampletones_application.tags.compose import TAG_SEPARATOR
from sampletones_shared.meta.source.classes import declared_subclasses
from sampletones_shared.meta.source.index import source_index
from sampletones_shared.meta.source.lookups import LookupSite, tree_lookups
from sampletones_shared.meta.source.modules import discover_modules, module_name
from sampletones_shared.meta.source.packages import package_directory
from sampletones_shared.meta.source.values import EnumMembers, EnumTable
from sampletones_shared.paths.source import SOURCE_ROOT

EnumPredicate = Callable[[object], bool]

APPLICATION_PACKAGE: Final[Path] = package_directory("sampletones_application")

RECEIVER_TYPE: Final[str] = "LanguageManager"
ELEMENT_BASE: Final[str] = AbstractElement.__name__

LANGUAGE_ENCODING: Final[str] = "utf-8"
ENTRY_SEPARATOR: Final[str] = ":"
COMMENT_PREFIX: Final[str] = "#"
FIRST_LINE: Final[int] = 1

BROKEN_LOOKUP: Final[str] = "broken lookup"
UNRESOLVED_PART: Final[str] = "unresolved part"
UNREACHED_ENTRY: Final[str] = "unreached entry"

DYNAMIC_KEY_RULE: Final[str] = (
    f"a key part arriving in a variable is annotated with a concrete element enum, never "
    f"{ELEMENT_BASE}, and a key an f-string builds states no values to check"
)


class Finding(NamedTuple):
    """One thing the check reports, named by kind and located where a reader can open it."""

    kind: str
    location: str
    message: str


def is_enum(member: object) -> bool:
    """States whether a module member is an enum."""
    return isinstance(member, EnumMeta)


def is_element_enum(member: object) -> bool:
    """States whether a module member is an enum of the elements a key part names."""
    return isinstance(member, EnumMeta) and issubclass(member, AbstractElement)


def enum_members(member_type: Type[Enum]) -> EnumMembers:
    """The value each member of an enum spells, keyed by member name."""
    return {member.name: str(member.value) for member in member_type}


def declared_enums(module: ModuleType, matches: EnumPredicate) -> Dict[str, EnumMembers]:
    """The enums a module declares itself, keyed by enum name.

    An enum is read from the module declaring it, so a name a module merely imports states its
    members once, under the module that owns it.

    Args:
        module: Imported module to read.
        matches: What makes a member one of the enums to read.

    Returns:
        Dict[str, EnumMembers]: Enum name to its member names and the values they spell.
    """
    return {
        name: enum_members(member_type)
        for name, member_type in inspect.getmembers(module, matches)
        if member_type.__module__ == module.__name__
    }


def element_enum_modules() -> List[ModuleType]:
    """Every module of the application declaring an element enum, imported for its members.

    A module is found by the classes it declares, so an enum naming a domain's own elements lives
    beside that domain and the check reads it there.

    Returns:
        List[ModuleType]: The imported modules, in path order.
    """
    return [
        importlib.import_module(module_name(module.path, SOURCE_ROOT))
        for module in discover_modules([APPLICATION_PACKAGE])
        if declared_subclasses(module.tree, ELEMENT_BASE)
    ]


def enum_table() -> EnumTable:
    """The members of every enum a key part can name, keyed by enum name.

    The hierarchy states the page, panel, and text type of a key, and an element enum states its
    element, so together they cover every part a lookup writes.

    Returns:
        EnumTable: Enum name to its member names and the values they spell.
    """
    table: Dict[str, EnumMembers] = declared_enums(hierarchy, is_enum)
    for module in element_enum_modules():
        table.update(declared_enums(module, is_element_enum))

    return table


def entry_key(line: str) -> Optional[str]:
    """The key a line of the language file states, where it states one."""
    key, separator, _ = line.partition(ENTRY_SEPARATOR)
    stripped = key.strip()
    if not separator or not stripped or stripped.startswith(COMMENT_PREFIX):
        return None

    return stripped


def entry_lines(path: Path) -> Dict[str, int]:
    """Where each key sits in the language file, read line by line."""
    lines: Dict[str, int] = {}
    for number, line in enumerate(path.read_text(encoding=LANGUAGE_ENCODING).splitlines(), start=FIRST_LINE):
        key = entry_key(line)
        if key is not None:
            lines.setdefault(key, number)

    return lines


def language_entries(path: Path) -> Dict[str, int]:
    """Every key the language file holds, paired with the line stating it.

    Args:
        path: Language file to read.

    Returns:
        Dict[str, int]: Key to its line, in file order.

    Raises:
        TypeError: If the file holds anything other than a mapping.
    """
    raw = yaml.safe_load(path.read_text(encoding=LANGUAGE_ENCODING))
    if not isinstance(raw, dict):
        raise TypeError(f"Language file {path} must hold a mapping, got {type(raw)}")

    lines = entry_lines(path)
    return {str(key): lines.get(str(key), FIRST_LINE) for key in raw}


def broken_lookups(sites: Sequence[LookupSite], entries: Mapping[str, int]) -> List[Finding]:
    """Every literal key a lookup asks for that the language file holds no entry for.

    Args:
        sites: Lookups read from the tree.
        entries: Keys the language file holds.

    Returns:
        List[Finding]: One finding per missing key.
    """
    return [
        Finding(
            kind=BROKEN_LOOKUP,
            location=site.location,
            message=f"the language file holds no entry for {key!r}",
        )
        for site in sites
        if site.exact
        for key in site.values
        if key not in entries
    ]


def unresolved_lookups(sites: Sequence[LookupSite]) -> List[Finding]:
    """Every lookup holding a part the check reads no values from.

    Args:
        sites: Lookups read from the tree.

    Returns:
        List[Finding]: One finding per lookup, naming the parts left unresolved.
    """
    return [
        Finding(
            kind=UNRESOLVED_PART,
            location=site.location,
            message=f"this lookup states {', '.join(site.unresolved_parts)}, which reaches no key: {DYNAMIC_KEY_RULE}",
        )
        for site in sites
        if not site.resolved
    ]


def unreached_entries(
    sites: Sequence[LookupSite],
    entries: Mapping[str, int],
    path: Path,
) -> List[Finding]:
    """Every entry of the language file no lookup asks for.

    Args:
        sites: Lookups read from the tree.
        entries: Keys the language file holds, paired with their lines.
        path: Language file the entries live in.

    Returns:
        List[Finding]: One finding per unreached entry, in file order.
    """
    reached = {key for site in sites for key in site.values}
    return [
        Finding(
            kind=UNREACHED_ENTRY,
            location=f"{path}:{line}",
            message=f"no lookup asks for {key!r}",
        )
        for key, line in entries.items()
        if key not in reached
    ]


def check_language_keys(source: Path, language_file: Path) -> List[Finding]:
    """Reads every lookup under a source root and holds it against a language file.

    Args:
        source: Root of the sources to read.
        language_file: Language file to check against.

    Returns:
        List[Finding]: Everything the check reports, broken lookups first.
    """
    modules = discover_modules([source])
    sites = tree_lookups(
        modules,
        index=source_index(modules),
        enums=enum_table(),
        receiver_type=RECEIVER_TYPE,
        separator=TAG_SEPARATOR,
    )
    entries = language_entries(language_file)
    return [
        *broken_lookups(sites, entries),
        *unresolved_lookups(sites),
        *unreached_entries(sites, entries, language_file),
    ]


def main(argv: Sequence[str]) -> int:
    """Report every disagreement between the language file and the lookups reading it."""
    parser = argparse.ArgumentParser(
        description="Check language keys against the language file, in both directions.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_ROOT,
        help="root of the sources to read",
    )
    parser.add_argument(
        "--language-file",
        type=Path,
        default=LANG_EN,
        help="language file to check against",
    )
    arguments = parser.parse_args(list(argv))

    findings = check_language_keys(arguments.source, arguments.language_file)
    if not findings:
        return 0

    print("Language key finding(s):", file=sys.stderr)
    for kind, location, message in findings:
        print(f"  [{kind}] {location}: {message}", file=sys.stderr)

    print(f"\nFound {len(findings)} language key finding(s).", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
