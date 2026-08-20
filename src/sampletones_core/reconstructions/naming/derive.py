from pathlib import Path
from typing import Final, Tuple, Type

from .protocol import NameRule
from .rules.common_directory import CommonDirectoryRule
from .rules.single_source import SingleSourceRule

SOURCE_RULES: Final[Tuple[Type[NameRule], ...]] = (
    SingleSourceRule,
    CommonDirectoryRule,
)


def derive_name(
    source_paths: Tuple[Path, ...],
    *,
    fallback_stem: str,
) -> str:
    """Names a reconstruction from its sources, falling back through the rule hierarchy.

    The first rule that applies derives the name: one source names after itself,
    several sources sharing one directory name after that directory, and the
    caller-supplied fallback stem names every other set of sources.
    """
    for rule_class in SOURCE_RULES:
        rule = rule_class()
        if rule.applies(source_paths):
            return rule.derive(source_paths)

    return fallback_stem
