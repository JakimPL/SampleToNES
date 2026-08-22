from typing import FrozenSet

from sampletones_player.compression.matches.index import PlaneIndex
from sampletones_player.compression.matches.matcher import PhraseMatcher
from sampletones_player.compression.options import CodecOptions
from sampletones_player.compression.parse.boundaries import Boundaries
from sampletones_player.compression.parse.literals import LiteralWindow
from sampletones_player.compression.parse.result import Parse
from sampletones_player.compression.parse.shortest import Shortest
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.compression.tokens.phrase import PhraseToken
from sampletones_player.compression.tokens.sizes import (
    hold_size,
    literal_size,
    phrase_size,
)
from sampletones_player.specification.compression import (
    MAX_HOLD_TICKS,
    MAX_LITERAL_BYTES,
    MAX_PHRASE_TICKS,
)


def _relax_literal(
    shortest: Shortest,
    plane: bytes,
    window: LiteralWindow,
    position: int,
    earliest: int,
) -> None:
    """Spelling the values out reaches ``position`` from wherever that costs least."""
    start = window.cheapest(position, earliest)
    cost = shortest.costs[start] + literal_size(position - start)
    if shortest.improves(position, cost):
        shortest.relax(start, position, cost, LiteralToken(values=plane[start:position]))


def _relax_forward(
    shortest: Shortest,
    index: PlaneIndex,
    matcher: PhraseMatcher,
    options: CodecOptions,
    position: int,
    reach: int,
    *,
    holdable: bool,
) -> None:
    """Everything a token starting at ``position`` may cover: a run held on, or a phrase played."""
    plane = index.plane
    cost = shortest.costs[position]
    if options.holds and holdable and plane[position] == plane[position - 1]:
        ticks = min(MAX_HOLD_TICKS, index.runs[position], reach)
        shortest.relax(
            position,
            position + ticks,
            cost + hold_size(),
            HoldToken(ticks=ticks),
        )

    if not options.phrases:
        return

    for phrase_id, ticks, transpose in matcher.matches(
        position,
        min(MAX_PHRASE_TICKS, reach),
        transposition=options.transposition,
    ):
        shortest.relax(
            position,
            position + ticks,
            cost + phrase_size(phrase_id, transpose),
            PhraseToken(phrase_id=phrase_id, ticks=ticks, transpose=transpose),
        )


def parse_plane(
    matcher: PhraseMatcher,
    options: CodecOptions,
    boundaries: FrozenSet[int],
) -> Parse:
    """Reads a plane as the cheapest token stream the dictionary allows.

    Every way of covering a tick is an edge — hold the value, spell it out, or play a phrase from
    there — and the cheapest path across them all is the encoding. Costs are the bytes each token
    takes, so the parse answers in the currency the program area is measured in.

    A boundary is a tick a token starts on, which is how a loop entry stays reachable: the stream
    is re-entered there, and a token that leans on the value the plane already reached starts
    elsewhere.

    Args:
        matcher: The plane, alongside the phrases it may play.
        options: Which of the codec's layers the encoding is built from.
        boundaries: The ticks a token starts on.

    Returns:
        Parse: The tokens the plane is written as, and what each of its prefixes costs.
    """
    index = matcher.index
    plane = index.plane
    ticks = index.ticks
    entries = Boundaries.across(ticks, boundaries)
    previous = entries.previous
    following = entries.following
    shortest = Shortest.across(ticks)
    window = LiteralWindow(shortest.costs)
    _relax_forward(shortest, index, matcher, options, 0, following[0], holdable=False)
    for position in range(1, ticks + 1):
        _relax_literal(
            shortest,
            plane,
            window,
            position,
            max(position - MAX_LITERAL_BYTES, previous[position]),
        )
        if position < ticks:
            _relax_forward(
                shortest,
                index,
                matcher,
                options,
                position,
                following[position] - position,
                holdable=position not in boundaries,
            )

    return Parse(tokens=shortest.walk(ticks), costs=tuple(shortest.costs))
