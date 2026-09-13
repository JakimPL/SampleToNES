import re
from typing import Final, List, Tuple, TypeAlias

NaturalSortKey: TypeAlias = Tuple[Tuple[int, str], ...]

_DIGIT_RUN_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+)")
LIST_SEPARATOR: Final[str] = ","


def natural_sort_key(text: str) -> NaturalSortKey:
    """
    Builds the sort key that orders text the way a reader expects.

    Digit runs compare as the numbers they spell, so `8 kHz` precedes `44.1 kHz`, and the text
    around them compares case-insensitively, so `Amen` and `amen` sit together. The text itself
    closes the key, so two labels reading alike keep a fixed order.

    Args:
        text: The label to order by.

    Returns:
        A tuple comparing as the reading order of the label.

    Examples:
        >>> sorted(["44.1 kHz", "8 kHz"], key=natural_sort_key)
        ['8 kHz', '44.1 kHz']
        >>> sorted(["track10", "track2"], key=natural_sort_key)
        ['track2', 'track10']
    """
    tokens = tuple(
        (int(part), "") if part.isdecimal() else (0, part.casefold()) for part in _DIGIT_RUN_PATTERN.split(text)
    )
    return tokens + ((0, text),)


def listed_items(stated: str) -> List[str]:
    """
    Reads a comma-separated list the way a command line states one.

    Each item keeps its own words with the spaces around it stripped, and an empty item, as a
    trailing comma leaves, is dropped.

    Args:
        stated: The list as written.

    Returns:
        The items, in the order written.

    Examples:
        >>> listed_items("pulse1, triangle,,noise,")
        ['pulse1', 'triangle', 'noise']
    """
    return [item.strip() for item in stated.split(LIST_SEPARATOR) if item.strip()]
