import logging
from dataclasses import replace
from typing import Final, List, Tuple

import pytest

from sampletones_player.compression.admit import admit_seeds
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.matches.cache import MatchCache
from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.parse.song import parse_planes
from sampletones_player.compression.progress.monitor import CodecMonitor
from sampletones_player.specification.binary import BYTE_VALUES
from sampletones_player.specification.compression import MAX_PHRASE_IDS
from sampletones_shared.utils.progress import silent_reporter

STREAM_START: Final[frozenset] = frozenset({0})
LEANED_ON: Final[bytes] = b"\x10\x18\x14\x22\x1c\x30\x11\x19\x15\x23\x1d\x31\x12\x1a\x16\x24"
PLAYED_SELDOM: Final[bytes] = b"\x60\x63\x67\x6c\x72\x79\x61\x64\x68\x6d\x73\x7a\x62\x65\x69\x6e"
LEANED_ON_REPEATS: Final[int] = 12
SELDOM_REPEATS: Final[int] = 4
RESTING_TICKS: Final[int] = 20
UNPLAYED_STEPS: Final[Tuple[int, ...]] = (0x40, 0x50)
UNPLAYED_PER_STEP: Final[int] = 160
UNRELATED: Final[bytes] = b"\x77\x77\x77"

PLANE: Final[bytes] = LEANED_ON * LEANED_ON_REPEATS + PLAYED_SELDOM * SELDOM_REPEATS + bytes(RESTING_TICKS)


def unplayed_seeds() -> Tuple[Phrase, ...]:
    """Phrases whose shape the plane holds nowhere, so none of them pays anything."""
    seeds: List[Phrase] = []
    for step in UNPLAYED_STEPS:
        for value in range(UNPLAYED_PER_STEP):
            seeds.append(
                Phrase(
                    body=bytes(
                        [
                            value,
                            (value + step) % BYTE_VALUES,
                            (value + 2 * step) % BYTE_VALUES,
                        ]
                    )
                )
            )

    return tuple(seeds)


@pytest.fixture(name="cache")
def cache_fixture() -> MatchCache:
    return MatchCache([PlaneIndex.from_plane(PLANE)])


@pytest.fixture(name="baseline")
def baseline_fixture(cache: MatchCache) -> Tuple[Parse, ...]:
    """The reading the plane takes when its tokens name no phrase at all."""
    return parse_planes(
        cache,
        phrase_table(()),
        replace(EVERY_LAYER, phrases=False),
        STREAM_START,
        CodecMonitor(silent_reporter),
    )


class TestSeedsTheDictionaryHasRoomFor:
    """Where every seed fits, every seed is offered and the settling decides what stays."""

    def test_every_seed_is_taken(self, cache: MatchCache, baseline: Tuple[Parse, ...]) -> None:
        seeds = (Phrase(body=LEANED_ON), Phrase(body=UNRELATED))
        table = admit_seeds(cache, seeds, baseline, EVERY_LAYER)
        assert table.phrases == seeds

    def test_a_shape_offered_twice_is_held_once(self, cache: MatchCache, baseline: Tuple[Parse, ...]) -> None:
        seed = Phrase(body=LEANED_ON)
        table = admit_seeds(cache, (seed, seed), baseline, EVERY_LAYER)
        assert table.phrases == (seed,)


class TestSeedsBeyondTheIdsATokenReaches:
    """Where the instruments offer more shapes than a token can name, payment decides."""

    def test_the_table_holds_the_ids_a_token_reaches(
        self,
        cache: MatchCache,
        baseline: Tuple[Parse, ...],
    ) -> None:
        table = admit_seeds(cache, crowded_seeds(), baseline, EVERY_LAYER)
        assert len(table) == MAX_PHRASE_IDS

    def test_the_shape_the_plane_leans_on_is_kept(
        self,
        cache: MatchCache,
        baseline: Tuple[Parse, ...],
    ) -> None:
        table = admit_seeds(cache, crowded_seeds(), baseline, EVERY_LAYER)
        assert Phrase(body=LEANED_ON) in table.phrases

    def test_the_shapes_the_plane_plays_outrank_the_ones_it_never_plays(
        self,
        cache: MatchCache,
        baseline: Tuple[Parse, ...],
    ) -> None:
        """The plane leans on one shape and reaches for another seldom, in that order."""
        table = admit_seeds(cache, crowded_seeds(), baseline, EVERY_LAYER)
        assert [table[0].body, table[1].body] == [LEANED_ON, PLAYED_SELDOM]

    def test_the_run_says_the_table_could_not_take_them_all(
        self,
        cache: MatchCache,
        baseline: Tuple[Parse, ...],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with caplog.at_level(logging.WARNING):
            admit_seeds(cache, crowded_seeds(), baseline, EVERY_LAYER)

        assert str(MAX_PHRASE_IDS) in caplog.text


def crowded_seeds() -> Tuple[Phrase, ...]:
    """More shapes than a token can name, two of which the plane actually plays."""
    return (*unplayed_seeds(), Phrase(body=LEANED_ON), Phrase(body=PLAYED_SELDOM))
