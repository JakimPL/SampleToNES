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

This script declares what the boundaries are; `sampletones_shared/meta/import_boundary/` holds how
they are read and reported.

Usage:
    python scripts/checks/import_boundary.py [files...]   # check specific files
    python scripts/checks/import_boundary.py --all        # run all rules against the source tree
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, Final, List, Sequence, Tuple

from sampletones_shared.meta.import_boundary.check import check_boundaries
from sampletones_shared.meta.import_boundary.graph import LayerGraph
from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.token import TokenRule
from sampletones_shared.paths.source import SOURCE_ROOT

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

PLAYER_LAYERS: Final[Dict[str, Tuple[str, ...]]] = {
    "__init__.py": (),
    "specification": (),
    "clock": ("specification",),
    "registers": ("specification",),
    "song.py": ("clock", "registers"),
    "builder.py": ("song.py", "registers", "clock"),
    "trace": ("song.py", "specification"),
    "nsf": ("song.py", "registers", "specification", "driver"),
    "export.py": ("builder.py", "nsf", "driver"),
    "driver": ("specification",),
    "driver/assembler": ("driver", "specification"),
}

PACKAGES: Final[LayerGraph] = LayerGraph(
    root="",
    package="",
    layers=PACKAGE_LAYERS,
)

PLAYER_GRAPH: Final[LayerGraph] = LayerGraph(
    root=PLAYER,
    package=PLAYER,
    layers=PLAYER_LAYERS,
)

APPLICATION_RULES: Final[Tuple[BoundaryRule, ...]] = (
    BoundaryRule(
        root=APPLICATION,
        pattern="config/**/*.py",
        forbidden=(
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.application",
        ),
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="logic/**/*.py",
        forbidden=(
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.services",
        ),
        contracts=SERVICE_CONTRACTS,
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="view_model/**/*.py",
        forbidden=(
            *VISUAL,
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
            "sampletones_application.services",
        ),
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="services/**/*.py",
        forbidden=(
            *VISUAL,
            "sampletones_application.view_model",
            "sampletones_application.coordinators",
            "sampletones_application.config",
            "sampletones_application.logic",
        ),
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="shell.py",
        forbidden=(
            "sampletones_application.logic",
            "sampletones_application.services",
        ),
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="coordinators/**/*.py",
        forbidden=(
            "sampletones_application.application",
            "sampletones_application.shell",
        ),
    ),
    BoundaryRule(
        root=APPLICATION,
        pattern="ui/**/*.py",
        forbidden=(
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
    *PACKAGES.rules(),
    *PLAYER_GRAPH.rules(),
    *APPLICATION_RULES,
)

TOKEN_RULES: Final[Tuple[TokenRule, ...]] = (
    TokenRule(
        root=APPLICATION,
        pattern="ui/panels/**/*.py",
        forbidden=r"\bSUF_PANEL_",
        message="ui/panels must not reference a column suffix (SUF_PANEL_*); a panel receives its "
        "parent through create_panel(parent), set by the coordinator that owns the layout",
    ),
    TokenRule(
        root=APPLICATION,
        pattern="ui/panels/**/*.py",
        forbidden=r"parent\s*=\s*TAG_SEQUENCER_TRACKER_PANEL\b",
        message="ui/panels must not parent into another panel's container (TAG_SEQUENCER_TRACKER_PANEL); "
        "the coordinator injects the parent through create_panel(parent)",
    ),
    TokenRule(
        root=APPLICATION,
        pattern="ui/panels/**/*.py",
        forbidden=r"\bTAG_GLOBAL_THEME_PANEL_(SURFACE|GROUND)\b",
        message="ui/panels must not bind a structural depth theme (TAG_GLOBAL_THEME_PANEL_SURFACE/"
        "GROUND); only the layout primitives own depth (TabColumns binds the column, card() "
        "binds the card), and a panel binds only semantic themes",
    ),
)


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
    violations = check_boundaries(arguments.source, RULES, TOKEN_RULES, selection)
    if not violations:
        return 0

    print("Layer boundary violation(s) found:", file=sys.stderr)
    for kind, location in violations:
        print(f"  [forbidden: {kind}] {location}", file=sys.stderr)

    print(f"\nFound {len(violations)} violation(s) in total.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
