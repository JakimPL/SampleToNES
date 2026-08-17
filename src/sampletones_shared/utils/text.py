import re
from typing import Final, Tuple, TypeAlias

NaturalSortKey: TypeAlias = Tuple[Tuple[int, str], ...]

_DIGIT_RUN_PATTERN: Final[re.Pattern[str]] = re.compile(r"(\d+)")


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
