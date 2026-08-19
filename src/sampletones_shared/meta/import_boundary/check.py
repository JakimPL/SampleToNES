from pathlib import Path
from typing import List, Optional, Sequence, Set

from sampletones_shared.meta.import_boundary.rule import BoundaryRule
from sampletones_shared.meta.import_boundary.scope import rule_modules
from sampletones_shared.meta.import_boundary.token import TokenRule
from sampletones_shared.meta.import_boundary.violation import Violation
from sampletones_shared.meta.source.modules import source_paths


def check_boundaries(
    source: Path,
    rules: Sequence[BoundaryRule],
    token_rules: Sequence[TokenRule],
    selection: Optional[Set[Path]],
) -> List[Violation]:
    """Every import and token the rules forbid under a source root.

    The tree is swept first, so the rules run over the modules it holds and a root reading as empty
    stops the check where it would otherwise report a clean tree.

    Args:
        source: Source root the rule roots are named within.
        rules: Import boundaries to hold the tree to.
        token_rules: Spellings to keep out of the tree.
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
        for rule in rules
        for path in rule_modules(
            source / rule.root,
            rule.pattern,
            rule.excluding,
            swept,
            selection,
        )
        for violation in rule.violations(path)
    ]
    violations.extend(
        violation
        for token_rule in token_rules
        for path in rule_modules(
            source / token_rule.root,
            token_rule.pattern,
            (),
            swept,
            selection,
        )
        for violation in token_rule.violations(path)
    )
    return violations
