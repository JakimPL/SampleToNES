from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.shortest import Shortest
from codec_study.sandbox.tokens import Literal, StudyToken
from sampletones_player.compression.parse.literals import LiteralWindow


def relax_literal(
    context: PlaneContext,
    shortest: Shortest[StudyToken],
    window: LiteralWindow,
    position: int,
    earliest: int,
) -> None:
    """Spelling the values out reaches ``position`` from wherever that costs least.

    Literals are the one token every grammar keeps, priced as the codec prices them: an opcode
    and the values, from the start the window finds cheapest.

    Args:
        context: The plane and the terms the grammar reads it on.
        shortest: The search the edge joins.
        window: The starts a literal ending here may take, the cheapest kept at the front.
        position: The tick the literal ends at.
        earliest: The earliest tick the literal may start on.
    """
    start = window.cheapest(position, earliest)
    cost = shortest.costs[start] + context.costs.literal(position - start)
    if shortest.improves(position, cost):
        shortest.relax(start, position, cost, Literal(values=context.index.plane[start:position]))
