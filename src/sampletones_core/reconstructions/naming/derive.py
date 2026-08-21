from pathlib import Path
from typing import Final, Tuple, Type

from .protocol import NameRule
from .rules.common_directory import CommonDirectoryRule
from .rules.common_prefix import CommonPrefixRule
from .rules.first_source import FirstSourceRule
from .rules.single_source import SingleSourceRule

SOURCE_RULES: Final[Tuple[Type[NameRule], ...]] = (
    SingleSourceRule,
    CommonDirectoryRule,
    CommonPrefixRule,
    FirstSourceRule,
)


def derive_name(
    source_paths: Tuple[Path, ...],
) -> str:
    """Names a reconstruction from its sources through the rule hierarchy.

    The first rule that applies derives the name: one source names after itself, sources
    sharing one directory name after that directory, sources sharing a deeper directory
    name after the deepest one they share, and every other set names after its first
    source.

    Raises:
        ValueError: If the source set is empty.
    """
    for rule_class in SOURCE_RULES:
        rule = rule_class()
        if rule.applies(source_paths):
            return rule.derive(source_paths)

    raise ValueError("Source paths must hold at least one path")
