from typing import Final, List, NamedTuple, Sequence, Set, Tuple

from sampletones_player.compression.dictionary.phrase import Phrase, phrase_entry_size
from sampletones_player.compression.dictionary.table import PhraseTable, phrase_table
from sampletones_player.compression.matches.cache import MIN_PHRASE_TICKS, MatchCache
from sampletones_player.compression.matches.shift import NO_SHIFT, asked_shift
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.tokens.sizes import phrase_size
from sampletones_player.specification.compression import MAX_PHRASE_IDS, PHRASE_ID_ESCAPE
from sampletones_shared.logger import logger

CROWDED_PHRASE_ID: Final[int] = PHRASE_ID_ESCAPE
UNSHIFTED_TOKEN_TRANSPOSE: Final[int] = 0
SHIFTED_TOKEN_TRANSPOSE: Final[int] = 1


class _Weighed(NamedTuple):
    payment: int
    order: int
    phrase: Phrase


class _Plays(NamedTuple):
    """What one plane pays a phrase, and how many tokens name it there."""

    paid: int
    tokens: int


def _distinct(seeds: Sequence[Phrase]) -> Tuple[Phrase, ...]:
    kept: List[Phrase] = []
    seen: Set[bytes] = set()
    for seed in seeds:
        if seed.body not in seen:
            seen.add(seed.body)
            kept.append(seed)

    return tuple(kept)


def _plays(
    cache: MatchCache,
    plane: int,
    phrase: Phrase,
    baseline: Parse,
    *,
    transposition: bool,
) -> _Plays:
    """What one plane pays a phrase, and how many tokens it names it in."""
    index = cache.index(plane)
    ticks = cache.reading(plane, phrase).ticks
    costs = baseline.costs
    origin = phrase.body[0]
    paid = 0
    played = 0
    position = 0
    while position < index.ticks:
        reach = ticks[position]
        shifted = asked_shift(index.plane[position], origin) != NO_SHIFT
        if reach >= MIN_PHRASE_TICKS and (transposition or not shifted):
            paid += costs[position + reach] - costs[position]
            played += 1
            position += reach
        else:
            position += 1

    return _Plays(paid=paid, tokens=played)


def _payment(
    cache: MatchCache,
    phrase: Phrase,
    baseline: Sequence[Parse],
    options: CodecOptions,
) -> int:
    """The bytes a phrase spares the song, its own entry and the tokens naming it taken off.

    A table crowded past its ids names most of its phrases through the escape byte, so every
    seed is weighed at what one of those tokens costs, which is the price they all compete at.
    """
    paid = 0
    played = 0
    for plane in range(len(cache.indices)):
        plays = _plays(
            cache,
            plane,
            phrase,
            baseline[plane],
            transposition=options.transposition,
        )
        paid += plays.paid
        played += plays.tokens

    if played == 0:
        return 0

    stated = phrase_size(CROWDED_PHRASE_ID, UNSHIFTED_TOKEN_TRANSPOSE)
    shifted = phrase_size(CROWDED_PHRASE_ID, SHIFTED_TOKEN_TRANSPOSE)
    spent = stated + shifted * (played - 1) + phrase_entry_size(phrase.length)
    return paid - spent


def _best_paying(
    cache: MatchCache,
    seeds: Sequence[Phrase],
    baseline: Sequence[Parse],
    options: CodecOptions,
) -> Tuple[Phrase, ...]:
    weighed = [
        _Weighed(
            payment=_payment(cache, seed, baseline, options),
            order=order,
            phrase=seed,
        )
        for order, seed in enumerate(seeds)
    ]
    weighed.sort(key=lambda entry: (-entry.payment, entry.order))
    return tuple(entry.phrase for entry in weighed[:MAX_PHRASE_IDS])


def admit_seeds(
    cache: MatchCache,
    seeds: Sequence[Phrase],
    baseline: Sequence[Parse],
    options: CodecOptions,
) -> PhraseTable:
    """Seeds the dictionary with the phrases a project's instruments offer.

    A token names one of a fixed number of phrases, and a project of many samples offers more
    shapes than that. The ones kept are the ones sparing the streams most, measured against a
    reading of the song that names no phrase at all, so a slot goes to the shape a song leans on
    rather than to whichever instrument the table happens to list first.

    Args:
        cache: The planes the song covers, alongside what each phrase plays against them.
        seeds: The phrases the song's instruments offer, in instrument-table order.
        baseline: The reading each plane takes when its tokens name no phrase.
        options: Which of the codec's layers the encoding is built from.

    Returns:
        PhraseTable: The seeds the dictionary takes.
    """
    offered = _distinct(seeds)
    if len(offered) <= MAX_PHRASE_IDS:
        return phrase_table(offered)

    logger.warning(
        f"the song's instruments offer {len(offered)} phrases and a dictionary holds "
        f"{MAX_PHRASE_IDS}, so the {MAX_PHRASE_IDS} sparing the streams most are kept"
    )
    return phrase_table(
        _best_paying(
            cache,
            offered,
            baseline,
            options,
        )
    )
