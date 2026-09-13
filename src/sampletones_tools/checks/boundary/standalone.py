import sys
from pathlib import Path
from typing import Final, List, Optional, Sequence, Set, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_tools.checks.boundary.imports import imported_module
from sampletones_tools.checks.boundary.lines import numbered_lines
from sampletones_tools.checks.boundary.scope import rule_modules
from sampletones_tools.checks.boundary.units import MODULE_SUFFIX
from sampletones_tools.checks.boundary.violation import Violation
from sampletones_tools.checks.source.modules import (
    MODULE_SEPARATOR,
    PACKAGE_INITIALIZER,
    SOURCE_PATTERN,
    source_paths,
)

SHADOWING: Final[str] = "stands in for a module the tree sits beside"


def local_names(root: Path) -> Set[str]:
    """The names a script under ``root`` reaches in the tree itself: its modules and its packages.

    A script runs with its tree on the import path, so a module beside it and a package holding
    an initializer are reached by their bare names.

    Args:
        root: The tree the scripts sit in.

    Returns:
        Set[str]: The importable names the tree offers.
    """
    modules = {path.stem for path in root.glob(SOURCE_PATTERN)}
    packages = {path.name for path in root.iterdir() if (path / f"{PACKAGE_INITIALIZER}{MODULE_SUFFIX}").is_file()}
    return modules | packages


class StandaloneRule(BaseModel):
    """One tree of scripts that run on the system interpreter, and what they may import.

    A script the rule reaches imports the standard library and the tree it sits in, so it runs
    on a machine that has Python and nothing more. The tree sits on the import path beside the
    standard library and the repository's own packages, so a name in it that stands in for one
    of theirs is reported as well.

    Attributes:
        pattern: Glob naming the scripts the rule reaches, written against the tree's root.
        excluding: Globs naming the scripts the rule leaves to the project environment.
        reserved: Names the tree keeps clear of beyond the standard library's.
        message: What the rule holds, printed where a script imports past it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    pattern: str
    excluding: Tuple[str, ...] = ()
    reserved: Tuple[str, ...] = ()
    message: str

    def violations(self, path: Path, local: Set[str]) -> List[Violation]:
        """Every import one script takes beyond the standard library and the tree.

        A relative import stays inside the tree by construction, and a name the tree offers is
        reached the way a script reaches it when run from the tree.

        Args:
            path: Script to read.
            local: The names the tree offers, as `local_names` reads them.

        Returns:
            List[Violation]: The imports the rule reports, in line order.

        Raises:
            OSError: If the script cannot be read.
        """
        violations: List[Violation] = []
        for line_number, line in numbered_lines(path):
            module = imported_module(line)
            if module is None:
                continue

            top = module.split(MODULE_SEPARATOR, 1)[0]
            if top and top not in sys.stdlib_module_names and top not in local:
                violations.append(Violation.at(self.message, path, line_number, line))

        return violations

    def shadowing(self, root: Path, paths: Sequence[Path]) -> List[Violation]:
        """Every name in the tree that stands in for a standard-library or reserved module.

        A name is reported once, at the first script that carries it, since a directory is
        named by every script under it.

        Args:
            root: The tree the scripts sit in, resolved.
            paths: The scripts the rule reaches, resolved and in path order.

        Returns:
            List[Violation]: One violation per offending name, in the order the tree is read.
        """
        taken = set(sys.stdlib_module_names) | set(self.reserved)
        seen: Set[str] = set()
        violations: List[Violation] = []
        for path in paths:
            for part in path.relative_to(root).with_suffix("").parts:
                if part in taken and part not in seen:
                    seen.add(part)
                    violations.append(Violation(kind=f"{part} {SHADOWING}", location=str(path)))

        return violations


def check_standalone(
    root: Path,
    rules: Sequence[StandaloneRule],
    selection: Optional[Set[Path]],
) -> List[Violation]:
    """Every import and name the rules forbid under a tree of standalone scripts.

    Args:
        root: The tree the rules are written against.
        rules: What the scripts may import.
        selection: Resolved paths to narrow the check to, or `None` to check the whole tree.

    Returns:
        List[Violation]: What the rules report, the shadowing names before the imports.

    Raises:
        NotADirectoryError: If the root names no directory.
        FileNotFoundError: If the root holds no module to read.
    """
    tree = root.resolve()
    swept = {path.resolve() for path in source_paths([tree])}
    local = local_names(tree)
    violations: List[Violation] = []
    for rule in rules:
        paths = rule_modules(tree, rule.pattern, rule.excluding, swept, selection)
        violations.extend(rule.shadowing(tree, paths))
        violations.extend(violation for path in paths for violation in rule.violations(path, local))

    return violations
