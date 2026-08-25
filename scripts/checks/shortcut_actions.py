#!/usr/bin/env python3

"""
Checks that every action a key or a menu item reaches is declared the whole way through.

An action is one `ShortcutId`, and naming it is the first of the links it needs: every shipped
keybinding scheme states the combination that fires it, `KeybindingActionElements` names it so the
keybindings editor can list it, and an application-scope action states the call it makes — either
its own entry in the shell's binding map, or membership of a family that maps a whole enum onto
one call.

The scheme a build loads validates itself as it loads, so this check covers what that validation
cannot reach: the schemes a platform other than this one ships, the editor's vocabulary, and the
call behind a menu item, which otherwise goes missing until the application is constructed.

Four things are reported:
    unanswered action  — an action a shipped scheme states no combination for
    unnamed action     — a rebindable action `KeybindingActionElements` has no member for
    uncalled action    — an application-scope action no binding and no family answers
    stale entry        — a name a scheme or the editor states that no action carries

Usage:
    python scripts/checks/shortcut_actions.py
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import (
    AbstractSet,
    Final,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    Sequence,
    Set,
)

import yaml

from sampletones_application.categories.elements import settings as settings_module
from sampletones_application.categories.elements.settings import (
    KeybindingActionElements,
)
from sampletones_application.paths import KEYBINDINGS_DIRECTORY
from sampletones_application.utils.gui.shortcuts import ids as ids_module
from sampletones_application.utils.gui.shortcuts.ids import (
    EDITABLE_SHORTCUT_CATEGORIES,
    FAMILY_SHORTCUT_IDS,
    ShortcutCategory,
    ShortcutId,
)
from sampletones_shared.meta.source.modules import SourceModule, parse_module
from sampletones_shared.meta.source.packages import package_directory

SHORTCUTS_MODULE: Final[Path] = Path(ids_module.__file__)
ELEMENTS_MODULE: Final[Path] = Path(settings_module.__file__)
SHELL_MODULE: Final[Path] = package_directory("sampletones_application") / "shell.py"

SCHEME_ENCODING: Final[str] = "utf-8"
SCHEME_BINDINGS_FIELD: Final[str] = "bindings"
SHORTCUT_ID_CLASS: Final[str] = "ShortcutId"

UNANSWERED_ACTION: Final[str] = "unanswered action"
UNNAMED_ACTION: Final[str] = "unnamed action"
UNCALLED_ACTION: Final[str] = "uncalled action"
STALE_ENTRY: Final[str] = "stale entry"

CALLED_RULE: Final[str] = (
    "an application-scope action states the call it makes, as an entry in the shell's binding map "
    "or as a member of FAMILY_SHORTCUT_IDS, whose call is dispatched from an enum"
)


class Finding(NamedTuple):
    """One thing the check reports, named by kind and located where a reader can open it."""

    kind: str
    location: str
    message: str


def editable_actions(actions: Iterable[ShortcutId]) -> FrozenSet[ShortcutId]:
    """The actions a reader may rebind, which is the set the keybindings editor lists.

    A dialog is operated by the keys its own category holds, so those stay as they are and the
    editor names them nowhere.
    """
    return frozenset(action for action in actions if action.category in EDITABLE_SHORTCUT_CATEGORIES)


def scheme_files(directory: Path = KEYBINDINGS_DIRECTORY) -> List[Path]:
    """Every keybinding scheme a directory ships, in name order."""
    return sorted(directory.glob("*.yaml"))


def scheme_actions(path: Path) -> Set[str]:
    """The action names one scheme states a combination for."""
    document = yaml.safe_load(path.read_text(encoding=SCHEME_ENCODING))
    bindings = (
        document.get(SCHEME_BINDINGS_FIELD)
        if isinstance(
            document,
            dict,
        )
        else None
    )
    return set(bindings) if isinstance(bindings, dict) else set()


def mapping_keys(module: SourceModule) -> Set[str]:
    """Every action a module names as a mapping key, which is how the shell states its calls.

    The shell builds its map inside the method that takes the bindings, so the map is read from the
    source rather than imported. Families are declared instead, and are read as what they declare.
    """
    return {
        key.attr
        for node in ast.walk(module.tree)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Attribute)
        and isinstance(
            key.value,
            ast.Name,
        )
        and key.value.id == SHORTCUT_ID_CLASS
    }


def unanswered_actions(
    schemes: Mapping[Path, Set[str]],
    actions: Iterable[ShortcutId],
) -> List[Finding]:
    """Every action a shipped scheme states no combination for."""
    return [
        Finding(
            kind=UNANSWERED_ACTION,
            location=str(path),
            message=f"this scheme states no combination for {action.value!r}",
        )
        for path, stated in schemes.items()
        for action in actions
        if action.value not in stated
    ]


def unnamed_actions(
    actions: Iterable[ShortcutId],
    named: AbstractSet[str],
) -> List[Finding]:
    """Every rebindable action the keybindings editor has no member to name."""
    return [
        Finding(
            kind=UNNAMED_ACTION,
            location=str(SHORTCUTS_MODULE),
            message=f"{action.name} has no KeybindingActionElements member, so the editor cannot list it",
        )
        for action in sorted(
            editable_actions(actions),
            key=lambda action: action.name,
        )
        if action.name not in named
    ]


def uncalled_actions(
    actions: Iterable[ShortcutId],
    answered: AbstractSet[str],
) -> List[Finding]:
    """Every application-scope action no call stands behind."""
    return [
        Finding(
            kind=UNCALLED_ACTION,
            location=str(SHELL_MODULE),
            message=f"{action.name} reaches no call: {CALLED_RULE}",
        )
        for action in actions
        if action.category is ShortcutCategory.APPLICATION and action.name not in answered
    ]


def stale_scheme_entries(
    schemes: Mapping[Path, Set[str]],
    actions: Iterable[ShortcutId],
) -> List[Finding]:
    """Every name a shipped scheme states that no action carries."""
    values = {action.value for action in actions}
    return [
        Finding(
            kind=STALE_ENTRY,
            location=str(path),
            message=f"{stated!r} names no action this build carries",
        )
        for path, entries in schemes.items()
        for stated in sorted(entries - values)
    ]


def stale_editor_entries(
    elements: Iterable[KeybindingActionElements],
    actions: Iterable[ShortcutId],
) -> List[Finding]:
    """Every name the keybindings editor states that no rebindable action carries."""
    names = {action.name for action in editable_actions(actions)}
    return [
        Finding(
            kind=STALE_ENTRY,
            location=str(ELEMENTS_MODULE),
            message=f"KeybindingActionElements.{element.name} names no action this build carries",
        )
        for element in elements
        if element.name not in names
    ]


def check() -> List[Finding]:
    """Every link of the chain, over every shipped scheme."""
    actions = tuple(ShortcutId)
    elements = tuple(KeybindingActionElements)
    schemes = {path: scheme_actions(path) for path in scheme_files()}
    answered = mapping_keys(parse_module(SHELL_MODULE)) | {action.name for action in FAMILY_SHORTCUT_IDS}
    named = {element.name for element in elements}

    return [
        *unanswered_actions(schemes, actions),
        *unnamed_actions(actions, named),
        *uncalled_actions(actions, answered),
        *stale_scheme_entries(schemes, actions),
        *stale_editor_entries(elements, actions),
    ]


def main(argv: Sequence[str]) -> int:
    """Report every action left short of a combination, a name, or the call it makes."""
    parser = argparse.ArgumentParser(
        description="Check that every action is declared the whole way through.",
    )
    parser.parse_args(list(argv))

    findings = check()
    if not findings:
        return 0

    print("Action(s) declared only part of the way:", file=sys.stderr)
    for kind, location, message in findings:
        print(f"  {kind} | {location}: {message}", file=sys.stderr)

    print(
        f"\nFound {len(findings)} incomplete action declaration(s).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
