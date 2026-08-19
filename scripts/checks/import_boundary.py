#!/usr/bin/env python3

"""
Enforces the import boundaries the source tree is layered by.

A layer graph names a tree of modules, the units it divides into, and the units each one may
import; every other unit is out of reach, so an edge across the graph is declared before it is
taken. The packages under `src/` are one such graph — `sampletones_core` sits below
`sampletones_player`, which is what keeps the reconstruction engine clear of the console player —
and the player's own subpackages are another, where `driver/assembler/` reaches the cc65 toolchain
and stays outside the wheel, so no shipped module imports it.

Boundary rules state a contract the other way round, by the import prefixes a directory stays clear
of, and carry the contract modules exempt from those prefixes: a layer may consume another layer's
data contract (e.g. a service's result types) while its implementation modules stay out of reach.
`sampletones_application` is layered that way.

Token rules additionally forbid a regex within a file glob, enforcing contracts a prefix cannot
express — e.g. that panels never compose a column suffix (`SUF_PANEL_*`) or parent into another
panel's container.

Usage:
    python scripts/checks/import_boundary.py [files...]   # check specific files
    python scripts/checks/import_boundary.py --all        # run all rules against the source tree
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Final, Iterable, List, NamedTuple, Optional, Sequence, Set, Tuple

from sampletones_shared.meta.source.modules import MODULE_SEPARATOR, source_paths
from sampletones_shared.paths.source import SOURCE_ROOT

IMPORT_RE = re.compile(r"^\s*(import|from)\s+([\w.]+)")

MODULE_SUFFIX: Final[str] = ".py"
PATH_SEPARATOR: Final[str] = "/"
UNIT_GLOB: Final[str] = "**/*.py"

APPLICATION: Final[str] = "sampletones_application"
PLAYER: Final[str] = "sampletones_player"

VISUAL: Final[Tuple[str, ...]] = (
    "dearpygui",
    "sampletones_application.ui",
    "sampletones_application.utils.gui",
)

SERVICE_CONTRACTS: Final[Tuple[str, ...]] = (
    "sampletones_application.services.result",
    "sampletones_application.services.render.result",
    "sampletones_application.services.song_player.result",
)

PACKAGE_LAYERS: Final[Dict[str, Tuple[str, ...]]] = {
    "sampletones_shared": (),
    "sampletones_config": (),
    "sampletones_assets": ("sampletones_shared",),
    "sampletones_synthesis": ("sampletones_shared",),
    "sampletones_core": ("sampletones_shared", "sampletones_synthesis"),
    "sampletones_player": ("sampletones_shared", "sampletones_core"),
    "sampletones_application": ("sampletones_shared", "sampletones_core", "sampletones_player"),
    "sampletones": ("sampletones_shared", "sampletones_core", "sampletones_application"),
}

SYNTHESIS_PITCH_CONTRACT: Final[Tuple[str, ...]] = (
    "sampletones_core.constants.general",
    "sampletones_core.utils.frequencies",
)

PACKAGE_CONTRACTS: Final[Dict[str, Tuple[str, ...]]] = {
    "sampletones_synthesis": SYNTHESIS_PITCH_CONTRACT,
}

PLAYER_LAYERS: Final[Dict[str, Tuple[str, ...]]] = {
    "__init__.py": (),
    "specification": (),
    "clock": ("specification",),
    "registers": ("specification",),
    "song.py": ("clock", "registers"),
    "trace": ("song.py", "specification"),
    "nsf": ("song.py", "registers", "specification", "driver"),
    "driver": ("specification",),
    "driver/assembler": ("driver", "specification"),
}


class LayerGraph(NamedTuple):
    """A tree of modules, the units it divides into, and what each unit may import.

    Attributes:
        root: Directory under the source root the units are named within.
        package: Import prefix the units sit under, empty where the units are packages themselves.
        layers: Each unit and the units it may import.
        contracts: Import prefixes a unit reaches past its layers.
    """

    root: str
    package: str
    layers: Dict[str, Tuple[str, ...]]
    contracts: Dict[str, Tuple[str, ...]]


class BoundaryRule(NamedTuple):
    """One tree of modules and the imports it stays clear of.

    Attributes:
        root: Directory under the source root the pattern is written against.
        pattern: Glob naming the modules the rule reaches.
        forbidden: Import prefixes out of reach in them.
        contracts: Import prefixes exempt from the forbidden ones.
        excluding: Globs naming the modules a rule of their own owns instead.
    """

    root: str
    pattern: str
    forbidden: Tuple[str, ...]
    contracts: Tuple[str, ...] = ()
    excluding: Tuple[str, ...] = ()


class TokenRule(NamedTuple):
    """One tree of modules and a spelling that stays out of them."""

    root: str
    pattern: str
    forbidden: str
    message: str


class Violation(NamedTuple):
    """One import or token a rule forbids, and where a reader opens it."""

    kind: str
    location: str


def unit_prefix(package: str, unit: str) -> str:
    """The import prefix a unit is reached by.

    Args:
        package: Import prefix the unit sits under, empty where the unit is a package itself.
        unit: Unit named as a path under the graph's root.

    Returns:
        str: The dotted prefix an import of that unit begins with.
    """
    name = unit.removesuffix(MODULE_SUFFIX).replace(PATH_SEPARATOR, MODULE_SEPARATOR)
    return f"{package}{MODULE_SEPARATOR}{name}" if package else name


def unit_glob(unit: str) -> str:
    """The glob naming the modules a unit holds, whether the unit is a module or a directory."""
    return unit if unit.endswith(MODULE_SUFFIX) else f"{unit}{PATH_SEPARATOR}{UNIT_GLOB}"


def nested_globs(unit: str, units: Iterable[str]) -> Tuple[str, ...]:
    """The globs of the units declared inside another one, which own their modules instead."""
    return tuple(unit_glob(other) for other in units if other.startswith(f"{unit}{PATH_SEPARATOR}"))


def layer_rules(graph: LayerGraph) -> List[BoundaryRule]:
    """One rule per unit of a layer graph, forbidding every unit its layers leave out.

    Declaring what a unit may import states the graph once, and the rule the check runs is what
    remains — so an edge the graph leaves out is reported wherever it is taken.

    Args:
        graph: The tree, its units, and the units each one may import.

    Returns:
        List[BoundaryRule]: The rules the graph amounts to, in declaration order.
    """
    return [
        BoundaryRule(
            root=graph.root,
            pattern=unit_glob(unit),
            forbidden=tuple(
                unit_prefix(graph.package, other) for other in graph.layers if other != unit and other not in allowed
            ),
            contracts=graph.contracts.get(unit, ()),
            excluding=nested_globs(unit, graph.layers),
        )
        for unit, allowed in graph.layers.items()
    ]


PACKAGES: Final[LayerGraph] = LayerGraph(
    root="",
    package="",
    layers=PACKAGE_LAYERS,
    contracts=PACKAGE_CONTRACTS,
)

PLAYER_GRAPH: Final[LayerGraph] = LayerGraph(
    root=PLAYER,
    package=PLAYER,
    layers=PLAYER_LAYERS,
    contracts={},
)

APPLICATION_RULES: Final[Tuple[BoundaryRule, ...]] = (
    BoundaryRule(
        APPLICATION,
        "config/**/*.py",
        (
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.application",
        ),
    ),
    BoundaryRule(
        APPLICATION,
        "logic/**/*.py",
        (
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.services",
        ),
        contracts=SERVICE_CONTRACTS,
    ),
    BoundaryRule(
        APPLICATION,
        "view_model/**/*.py",
        (
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
            "sampletones_application.services",
        ),
    ),
    BoundaryRule(
        APPLICATION,
        "services/**/*.py",
        (
            *VISUAL,
            "sampletones_application.view_model",
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
        ),
    ),
    BoundaryRule(
        APPLICATION,
        "shell.py",
        (
            "sampletones_application.logic",
            "sampletones_application.services",
        ),
    ),
    BoundaryRule(
        APPLICATION,
        "coordinators/**/*.py",
        (
            "sampletones_application.application",
            "sampletones_application.shell",
        ),
    ),
    BoundaryRule(
        APPLICATION,
        "ui/**/*.py",
        (
            "sampletones_application.coordinators",
            "sampletones_application.logic",
            "sampletones_application.services",
            "sampletones_application.config",
            "sampletones_application.application",
            "sampletones_application.shell",
            "sampletones_application.utils.gui.dialogs",
        ),
    ),
)


RULES: Final[Tuple[BoundaryRule, ...]] = (
    *layer_rules(PACKAGES),
    *layer_rules(PLAYER_GRAPH),
    *APPLICATION_RULES,
)


TOKEN_RULES: Final[Tuple[TokenRule, ...]] = (
    TokenRule(
        APPLICATION,
        "ui/panels/**/*.py",
        r"\bSUF_PANEL_",
        "ui/panels must not reference a column suffix (SUF_PANEL_*); a panel receives its "
        "parent through create_panel(parent), set by the coordinator that owns the layout",
    ),
    TokenRule(
        APPLICATION,
        "ui/panels/**/*.py",
        r"parent\s*=\s*TAG_SEQUENCER_TRACKER_PANEL\b",
        "ui/panels must not parent into another panel's container (TAG_SEQUENCER_TRACKER_PANEL); "
        "the coordinator injects the parent through create_panel(parent)",
    ),
    TokenRule(
        APPLICATION,
        "ui/panels/**/*.py",
        r"\bTAG_GLOBAL_THEME_PANEL_(SURFACE|GROUND)\b",
        "ui/panels must not bind a structural depth theme (TAG_GLOBAL_THEME_PANEL_SURFACE/"
        "GROUND); only the layout primitives own depth (TabColumns binds the column, card() "
        "binds the card), and a panel binds only semantic themes",
    ),
)


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(prefix + MODULE_SEPARATOR)


def find_token_violations(
    filepath: Path,
    rule: TokenRule,
) -> List[Violation]:
    pattern = re.compile(rule.forbidden)
    violations: List[Violation] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        if pattern.search(line):
            location = f"{filepath}:{line_number}"
            violations.append(
                Violation(
                    kind=rule.message,
                    location=f"{location}: {line.strip()}",
                )
            )

    return violations


def find_violations(
    filepath: Path,
    rule: BoundaryRule,
) -> List[Violation]:
    violations: List[Violation] = []
    for line_number, line in enumerate(
        filepath.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        match = IMPORT_RE.match(line)
        if match is None:
            continue

        module = match.group(2)
        if any(_matches_prefix(module, contract) for contract in rule.contracts):
            continue

        for prefix in rule.forbidden:
            if _matches_prefix(module, prefix):
                location = f"{filepath}:{line_number}"
                violations.append(
                    Violation(
                        kind=prefix,
                        location=f"{location}: {line.strip()}",
                    )
                )
                break

    return violations


def rule_modules(
    root: Path,
    pattern: str,
    excluding: Tuple[str, ...],
    swept: Set[Path],
    selection: Optional[Set[Path]],
) -> List[Path]:
    """The modules a rule reaches, in path order.

    A rule names its files by one glob whether the check runs over the whole tree or over the files
    a hook lists, so the two entry points read the same rule the same way. A module a nested rule
    owns belongs to that rule alone, which is how a subpackage states a boundary of its own inside
    the one around it.

    Args:
        root: Directory the rule globs are written against.
        pattern: Glob the rule names its files by.
        excluding: Globs naming the modules a rule of their own owns instead.
        swept: Visible modules the tree holds, which the glob is held to.
        selection: Resolved paths to narrow the rule to, or `None` to reach every module it names.

    Returns:
        List[Path]: The modules the rule applies to.
    """
    owned = {path.resolve() for nested in excluding for path in root.glob(nested)}
    matched = ({path.resolve() for path in root.glob(pattern)} & swept) - owned
    if selection is not None:
        matched &= selection

    return sorted(matched)


def check_boundaries(source: Path, selection: Optional[Set[Path]]) -> List[Violation]:
    """Every import and token the rules forbid under a source root.

    The tree is swept first, so the rules run over the modules it holds and a root reading as empty
    stops the check where it would otherwise report a clean tree.

    Args:
        source: Source root the rule roots are named within.
        selection: Resolved paths to narrow the check to, or `None` to check the whole tree.

    Returns:
        List[Violation]: What the rules report, boundary rules first.

    Raises:
        NotADirectoryError: If the source root names no directory.
        FileNotFoundError: If the source root holds no module to read.
    """
    swept = {path.resolve() for path in source_paths([source])}
    violations = [
        violation
        for rule in RULES
        for filepath in rule_modules(source / rule.root, rule.pattern, rule.excluding, swept, selection)
        for violation in find_violations(filepath, rule)
    ]
    violations.extend(
        violation
        for token_rule in TOKEN_RULES
        for filepath in rule_modules(source / token_rule.root, token_rule.pattern, (), swept, selection)
        for violation in find_token_violations(filepath, token_rule)
    )
    return violations


def main(argv: Sequence[str]) -> int:
    """Report every import and token the layer boundaries forbid."""
    parser = argparse.ArgumentParser(
        description="Check the import boundaries the source tree is layered by.",
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
        help=f"check every module under {SOURCE_ROOT.name}/ instead of named files",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=SOURCE_ROOT,
        help="source root the rule roots are named within",
    )
    arguments = parser.parse_args(list(argv))

    files: List[Path] = arguments.files
    selection = None if arguments.all else {path.resolve() for path in files}
    violations = check_boundaries(arguments.source, selection)
    if not violations:
        return 0

    print("Layer boundary violation(s) found:", file=sys.stderr)
    for kind, location in violations:
        print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

    print(f"\nFound {len(violations)} violation(s) in total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
