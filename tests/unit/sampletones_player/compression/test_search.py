from random import Random
from typing import Final, FrozenSet

import pytest

from sampletones_player.compression.budget import SearchBudget
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.progress.monitor import CodecMonitor
from sampletones_player.compression.search import search_phrases
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_shared.utils.progress import silent_reporter

STREAM_START: Final[FrozenSet[int]] = frozenset({0})
FIGURE: Final[bytes] = b"\x10\x18\x14\x22\x1c\x30\x11\x19\x15\x23\x1d\x31\x12\x1a\x16\x24"
FIGURE_REPEATS: Final[int] = 6
CROWDED_TICKS: Final[int] = 600
CROWDED_SEED: Final[int] = 20260912
REPEATING: Final[bytes] = FIGURE * FIGURE_REPEATS
NARROW_ENTRIES: Final[int] = 8_000


def _crowded() -> bytes:
    """A plane of unrelated values, which offers many candidates and repeats none of them."""
    random = Random(CROWDED_SEED)
    return bytes(random.randrange(BYTE_VALUES) for _ in range(CROWDED_TICKS))


def _searched(budget: SearchBudget) -> PhraseTable:
    cache = MatchCache([PlaneIndex.from_plane(_crowded()), PlaneIndex.from_plane(REPEATING)])
    return search_phrases(
        cache,
        phrase_table(()),
        EVERY_LAYER,
        STREAM_START,
        CodecMonitor(silent_reporter),
        budget,
    )


@pytest.fixture(name="narrow")
def narrow_fixture() -> SearchBudget:
    """A round too small for the crowded plane alone, and ample for the repeating one."""
    return SearchBudget(candidate_entries=NARROW_ENTRIES, rounds=64, confirmed_candidates=3)


class TestEveryPlaneIsHeardFrom:
    """A crowded plane takes its share of a round and leaves the rest to the planes after it."""

    def test_a_plane_after_a_crowded_one_earns_its_phrase(self, narrow: SearchBudget) -> None:
        table = _searched(narrow)
        assert any(phrase.body in REPEATING for phrase in table.phrases)

    def test_the_crowded_plane_earns_nothing(self, narrow: SearchBudget) -> None:
        crowded = _crowded()
        table = _searched(narrow)
        assert all(phrase.body not in crowded for phrase in table.phrases)


class TestTheRoundsBoundWhatTheSearchEarns:
    """Each round adds at most one phrase, so the rounds cap the dictionary the search fills."""

    def test_no_rounds_leaves_the_table_as_seeded(self) -> None:
        table = _searched(SearchBudget(candidate_entries=NARROW_ENTRIES, rounds=0, confirmed_candidates=3))
        assert len(table) == 0

    def test_one_round_adds_one_phrase(self) -> None:
        table = _searched(SearchBudget(candidate_entries=NARROW_ENTRIES, rounds=1, confirmed_candidates=3))
        assert len(table) == 1
