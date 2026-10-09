from typing import Final, List, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field


class SearchBudget(BaseModel):
    """How much work the search spends on the phrases a song's own planes repeat.

    A round gathers candidate windows from what the parse still spells out, ranks them, and
    confirms the best few by parsing the song again with each one added. Each figure here
    bounds one of those steps, so the budget is what an export trades against the bytes the
    search earns.

    Attributes:
        candidate_entries: The candidate windows one round gathers over every plane together,
            shared among the planes by what each has to offer.
        rounds: The rounds the search runs, each adding at most one phrase.
        confirmed_candidates: The best-ranked candidates a round parses the song again with.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    candidate_entries: int = Field(ge=1)
    rounds: int = Field(ge=0)
    confirmed_candidates: int = Field(ge=1)


DEFAULT_SEARCH_BUDGET: Final[SearchBudget] = SearchBudget(
    candidate_entries=200_000,
    rounds=64,
    confirmed_candidates=3,
)


def shares(
    demands: Sequence[int],
    total: int,
) -> Tuple[int, ...]:
    """Divides ``total`` among claimants, meeting small demands in full and splitting what
    remains evenly among the larger ones.

    Claimants are served from the smallest demand upward, each taking the lesser of its demand
    and an even share of what is left, so a claimant asking for little leaves its surplus to the
    rest and a claimant asking for much is held to the same share as its peers.

    Args:
        demands: What each claimant would take, given the room.
        total: What there is to share.

    Returns:
        Tuple[int, ...]: What each claimant receives, in the order the demands were given.
    """
    granted: List[int] = [0] * len(demands)
    remaining = total
    pending = len(demands)
    for claimant in sorted(range(len(demands)), key=lambda index: demands[index]):
        granted[claimant] = min(demands[claimant], remaining // pending)
        remaining -= granted[claimant]
        pending -= 1

    return tuple(granted)
