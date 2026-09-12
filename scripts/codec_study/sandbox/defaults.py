from collections import Counter
from typing import Final, List, Sequence, Tuple

from codec_study.sandbox.parse import StudyParse
from codec_study.sandbox.tokens import Play

NO_DEFAULT: Final[int] = 0


def no_defaults(phrases: int) -> Tuple[int, ...]:
    """A default count for none of ``phrases`` phrases."""
    return (NO_DEFAULT,) * phrases


def modal_counts(
    parses: Sequence[StudyParse],
    phrases: int,
) -> Tuple[int, ...]:
    """The count each phrase is played at most often across the parses (H4).

    A phrase's default count is the one its tokens would leave unstated most often, so it is
    read off the parse as it stands. A phrase the parses never play keeps no default.

    Args:
        parses: Every plane's parse.
        phrases: The phrases the table holds.

    Returns:
        Tuple[int, ...]: The default count of each phrase, by id, zero where it has none.
    """
    counters: List[Counter[int]] = [Counter() for _ in range(phrases)]
    for parse in parses:
        for token in parse.tokens:
            if isinstance(token, Play):
                counters[token.phrase_id][token.ticks] += 1

    return tuple(_modal(counter) for counter in counters)


def _modal(counter: Counter[int]) -> int:
    if not counter:
        return NO_DEFAULT

    return min(counter, key=lambda ticks: (-counter[ticks], ticks))
