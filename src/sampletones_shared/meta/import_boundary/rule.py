from pathlib import Path
from typing import List, Tuple

from pydantic import BaseModel, ConfigDict

from sampletones_shared.meta.import_boundary.imports import (
    imported_module,
    matches_prefix,
)
from sampletones_shared.meta.import_boundary.lines import numbered_lines
from sampletones_shared.meta.import_boundary.violation import Violation


class BoundaryRule(BaseModel):
    """One tree of modules and the imports it stays clear of.

    Attributes:
        root: Directory under the source root the pattern is written against.
        pattern: Glob naming the modules the rule reaches.
        forbidden: Import prefixes out of reach in them.
        contracts: Import prefixes exempt from the forbidden ones.
        excluding: Globs naming the modules a rule of their own owns instead.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str
    pattern: str
    forbidden: Tuple[str, ...]
    contracts: Tuple[str, ...] = ()
    excluding: Tuple[str, ...] = ()

    def violations(self, path: Path) -> List[Violation]:
        """Every import one module takes that the rule forbids.

        A contract is read first, so a module named by one is reached even where the prefix around
        it is out of bounds. The first forbidden prefix an import matches names the violation, since
        one import crosses one boundary.

        Args:
            path: Module to read.

        Returns:
            List[Violation]: What the module imports past the boundary, in line order.

        Raises:
            OSError: If the module cannot be read.
        """
        violations: List[Violation] = []
        for line_number, line in numbered_lines(path):
            module = imported_module(line)
            if module is None or any(
                matches_prefix(
                    module,
                    contract,
                )
                for contract in self.contracts
            ):
                continue

            crossed = next(
                (
                    prefix
                    for prefix in self.forbidden
                    if matches_prefix(
                        module,
                        prefix,
                    )
                ),
                None,
            )
            if crossed is not None:
                violations.append(
                    Violation.at(
                        crossed,
                        path,
                        line_number,
                        line,
                    )
                )

        return violations
