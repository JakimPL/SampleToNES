from time import process_time
from typing import Callable, Final, Sequence, Tuple

from sampletones_player.compression.budget import DEFAULT_SEARCH_BUDGET, SearchBudget
from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.encode import encode_planes
from sampletones_player.compression.options import EVERY_LAYER
from sampletones_tools.codec.study.corpus.song import StudySong
from sampletones_tools.codec.study.measure import Encoder, Encoding, production_encoding
from sampletones_tools.codec.study.variants.seeds import split, trimmed, whole_and_split
from sampletones_tools.codec.study.variants.variant import Variant, VariantKind

SeedTransform = Callable[[Sequence[Phrase]], Tuple[Phrase, ...]]

BASELINE_NAME: Final[str] = "baseline"
NO_LOOP_BOUNDARIES: Final[frozenset[int]] = frozenset()
SEED_SPLITTING: Final[str] = "H2'"
SEARCH_BUDGET: Final[str] = "H8"
DRIVER_UNCHANGED: Final[str] = "driver unchanged"
SPLIT_THRESHOLDS: Final[Tuple[int, ...]] = (2, 3, 4, 6, 8)
LIGHT_ENTRIES: Final[int] = 50_000
WIDE_ENTRIES: Final[int] = 1_000_000
LONG_ROUNDS: Final[int] = 255
LIGHT_CONFIRMED: Final[int] = 1
DEEP_CONFIRMED: Final[int] = 8


def compress(
    song: StudySong,
    *,
    seeds: Sequence[Phrase],
    budget: SearchBudget,
) -> CompressedPlanes:
    """Compresses a song as the export does, every layer on, over the seeds and budget given.

    Args:
        song: The song to compress.
        seeds: The phrases offered to the dictionary.
        budget: How much work the search spends.

    Returns:
        CompressedPlanes: The dictionary and the token streams.
    """
    return encode_planes(
        song.planes,
        seeds,
        options=EVERY_LAYER,
        boundaries=NO_LOOP_BOUNDARIES,
        budget=budget,
    )


def compress_baseline(song: StudySong) -> CompressedPlanes:
    """Compresses a song as the export does today.

    Args:
        song: The song to compress.

    Returns:
        CompressedPlanes: The dictionary and the token streams.
    """
    return compress(song, seeds=song.seeds, budget=DEFAULT_SEARCH_BUDGET)


def encode_production(
    song: StudySong,
    *,
    seeds: Sequence[Phrase],
    budget: SearchBudget,
) -> Encoding:
    """Encodes a song as the export does, timing the run and playing the result back.

    Args:
        song: The song to encode.
        seeds: The phrases offered to the dictionary.
        budget: How much work the search spends.

    Returns:
        Encoding: The encoding, its streams kept as written.
    """
    started = process_time()
    compressed = compress(song, seeds=seeds, budget=budget)
    return production_encoding(song, compressed, process_time() - started)


def seed_encoder(transform: SeedTransform) -> Encoder:
    """An encoder offering the dictionary the song's seeds after ``transform``.

    Args:
        transform: What the seeds become before they are offered.

    Returns:
        Encoder: The encoder, searching at the default budget.
    """

    def encode(song: StudySong) -> Encoding:
        return encode_production(song, seeds=transform(song.seeds), budget=DEFAULT_SEARCH_BUDGET)

    return encode


def budget_encoder(budget: SearchBudget) -> Encoder:
    """An encoder searching under ``budget`` over the song's own seeds.

    Args:
        budget: How much work the search spends.

    Returns:
        Encoder: The encoder.
    """

    def encode(song: StudySong) -> Encoding:
        return encode_production(song, seeds=song.seeds, budget=budget)

    return encode


def _seed_variant(
    name: str,
    transform: SeedTransform,
) -> Variant:
    return Variant(
        name=name,
        hypothesis=SEED_SPLITTING,
        kind=VariantKind.ENCODER,
        note=DRIVER_UNCHANGED,
        encode=seed_encoder(transform),
        needs_seeds=True,
    )


def _budget_variant(
    name: str,
    budget: SearchBudget,
) -> Variant:
    return Variant(
        name=name,
        hypothesis=SEARCH_BUDGET,
        kind=VariantKind.ENCODER,
        note=DRIVER_UNCHANGED,
        encode=budget_encoder(budget),
        needs_seeds=False,
    )


def _splitter(threshold: int) -> SeedTransform:
    return lambda seeds: split(seeds, threshold)


def _both(threshold: int) -> SeedTransform:
    return lambda seeds: whole_and_split(seeds, threshold)


SEED_VARIANTS: Final[Tuple[Variant, ...]] = (
    _seed_variant("seeds-trimmed", trimmed),
    *(_seed_variant(f"seeds-split-{threshold}", _splitter(threshold)) for threshold in SPLIT_THRESHOLDS),
    *(_seed_variant(f"seeds-both-{threshold}", _both(threshold)) for threshold in SPLIT_THRESHOLDS),
)

BUDGET_VARIANTS: Final[Tuple[Variant, ...]] = (
    _budget_variant(
        "search-light",
        SearchBudget(
            candidate_entries=LIGHT_ENTRIES,
            rounds=DEFAULT_SEARCH_BUDGET.rounds,
            confirmed_candidates=LIGHT_CONFIRMED,
        ),
    ),
    _budget_variant(
        "search-long",
        SearchBudget(
            candidate_entries=DEFAULT_SEARCH_BUDGET.candidate_entries,
            rounds=LONG_ROUNDS,
            confirmed_candidates=DEFAULT_SEARCH_BUDGET.confirmed_candidates,
        ),
    ),
    _budget_variant(
        "search-wide",
        SearchBudget(
            candidate_entries=WIDE_ENTRIES,
            rounds=DEFAULT_SEARCH_BUDGET.rounds,
            confirmed_candidates=DEFAULT_SEARCH_BUDGET.confirmed_candidates,
        ),
    ),
    _budget_variant(
        "search-deep",
        SearchBudget(
            candidate_entries=WIDE_ENTRIES,
            rounds=LONG_ROUNDS,
            confirmed_candidates=DEEP_CONFIRMED,
        ),
    ),
)
