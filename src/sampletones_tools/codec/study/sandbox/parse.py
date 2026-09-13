from dataclasses import dataclass
from typing import List, Sequence, Tuple

from sampletones_player.compression.parse.literals import LiteralWindow
from sampletones_player.specification.compression import MAX_LITERAL_BYTES
from sampletones_tools.codec.study.sandbox.context import PlaneContext
from sampletones_tools.codec.study.sandbox.edges.generator import EdgeGenerator
from sampletones_tools.codec.study.sandbox.edges.holds import (
    hold_edges,
    wide_hold_edges,
)
from sampletones_tools.codec.study.sandbox.edges.literals import relax_literal
from sampletones_tools.codec.study.sandbox.edges.phrases import phrase_edges
from sampletones_tools.codec.study.sandbox.edges.set_hold import set_hold_edges
from sampletones_tools.codec.study.sandbox.grammar import Grammar
from sampletones_tools.codec.study.sandbox.shortest import Shortest
from sampletones_tools.codec.study.sandbox.tokens import StudyToken


@dataclass(frozen=True)
class StudyParse:
    """A plane read as the tokens of one grammar, alongside what each of its prefixes costs.

    Attributes:
        tokens: The tokens the plane is written as, in the order they are read.
        costs: The bytes each prefix of the plane takes, the whole plane's cost last.
    """

    tokens: Tuple[StudyToken, ...]
    costs: Tuple[int, ...]

    @property
    def size(self) -> int:
        """The bytes the plane's token stream takes."""
        return self.costs[-1]


def generators(grammar: Grammar) -> Tuple[EdgeGenerator, ...]:
    """The token kinds a grammar offers from a tick, each as the edges it adds to the search.

    Args:
        grammar: The grammar.

    Returns:
        Tuple[EdgeGenerator, ...]: The generators, holds first and phrases last.
    """
    chosen: List[EdgeGenerator] = [hold_edges(every_length=grammar.every_length)]
    if grammar.wide_hold:
        chosen.append(wide_hold_edges(every_length=grammar.every_length))

    if grammar.set_hold:
        chosen.append(set_hold_edges(every_length=grammar.every_length))

    chosen.append(phrase_edges(defaults=grammar.default_counts))
    return tuple(chosen)


def _relax_forward(
    offered: Sequence[EdgeGenerator],
    context: PlaneContext,
    shortest: Shortest[StudyToken],
    position: int,
    reach: int,
    *,
    holdable: bool,
) -> None:
    for generator in offered:
        generator(
            context,
            shortest,
            position,
            reach,
            holdable=holdable,
        )


def parse_plane(
    context: PlaneContext,
    grammar: Grammar,
) -> StudyParse:
    """Reads a plane as the cheapest token stream ``grammar`` allows.

    This is the production parse with the token kinds plugged in: literals reach every tick
    from their cheapest start, and the grammar's other kinds are offered forward from each tick
    a token may start on.

    Args:
        context: The plane and the terms the grammar reads it on.
        grammar: The grammar.

    Returns:
        StudyParse: The tokens the plane is written as, and what each of its prefixes costs.
    """
    ticks = context.index.ticks
    entries = context.boundaries
    previous = entries.previous
    following = entries.following
    offered = generators(grammar)
    shortest: Shortest[StudyToken] = Shortest.across(ticks)
    window = LiteralWindow(shortest.costs)
    _relax_forward(
        offered,
        context,
        shortest,
        0,
        following[0],
        holdable=grammar.start_hold,
    )
    for position in range(1, ticks + 1):
        relax_literal(
            context,
            shortest,
            window,
            position,
            max(position - MAX_LITERAL_BYTES, previous[position]),
        )
        if position < ticks:
            _relax_forward(
                offered,
                context,
                shortest,
                position,
                following[position] - position,
                holdable=position not in entries.entries,
            )

    return StudyParse(
        tokens=shortest.walk(ticks),
        costs=tuple(shortest.costs),
    )
