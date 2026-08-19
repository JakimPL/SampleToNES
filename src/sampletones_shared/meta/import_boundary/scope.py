from pathlib import Path
from typing import List, Optional, Set, Tuple


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
