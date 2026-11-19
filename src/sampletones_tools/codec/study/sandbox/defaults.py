from typing import Sequence, Tuple

from sampletones_player.compression.dictionary.defaults import modal_counts as phrase_modal_counts
from sampletones_player.specification.compression import NO_DEFAULT_COUNT
from sampletones_tools.codec.study.sandbox.parse import StudyParse
from sampletones_tools.codec.study.sandbox.tokens import Play


def no_defaults(phrases: int) -> Tuple[int, ...]:
    """A default count for none of ``phrases`` phrases."""
    return (NO_DEFAULT_COUNT,) * phrases


def modal_counts(
    parses: Sequence[StudyParse],
    phrases: int,
) -> Tuple[int, ...]:
    """The count each phrase is played at most often across the parses (H4), by the player's rule.

    Args:
        parses: Every plane's parse.
        phrases: The phrases the table holds.

    Returns:
        Tuple[int, ...]: The default count of each phrase, by id, zero where it has none.
    """
    plays = ((token.phrase_id, token.ticks) for parse in parses for token in parse.tokens if isinstance(token, Play))
    return phrase_modal_counts(plays, phrases)
