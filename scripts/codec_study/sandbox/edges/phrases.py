from codec_study.sandbox.context import PlaneContext
from codec_study.sandbox.edges.generator import EdgeGenerator
from codec_study.sandbox.shortest import Shortest
from codec_study.sandbox.tokens import Play, StudyToken
from sampletones_player.specification.compression import MAX_PHRASE_TICKS


def phrase_edges(*, defaults: bool) -> EdgeGenerator:
    """Phrases, as the codec offers them: each one the plane plays from the tick, played whole.

    With defaults on, a phrase played at least its default count from the tick is offered at
    that count too, as the token that carries no count of its own (H4).

    Args:
        defaults: Whether the default-count token is offered.

    Returns:
        EdgeGenerator: The generator.
    """

    def relax(
        context: PlaneContext,
        shortest: Shortest[StudyToken],
        position: int,
        reach: int,
        *,
        holdable: bool,
    ) -> None:
        del holdable
        cost = shortest.costs[position]
        costs = context.costs
        for phrase_id, ticks, transpose in context.matcher.matches(
            position,
            min(MAX_PHRASE_TICKS, reach),
            transposition=context.transposition,
        ):
            stated = cost + costs.phrase(phrase_id, transpose, default=False)
            if shortest.improves(position + ticks, stated):
                shortest.relax(
                    position,
                    position + ticks,
                    stated,
                    Play(phrase_id=phrase_id, ticks=ticks, transpose=transpose, default=False),
                )

            count = context.defaults[phrase_id] if defaults else 0
            if 0 < count <= ticks:
                unstated = cost + costs.phrase(phrase_id, transpose, default=True)
                if shortest.improves(position + count, unstated):
                    shortest.relax(
                        position,
                        position + count,
                        unstated,
                        Play(phrase_id=phrase_id, ticks=count, transpose=transpose, default=True),
                    )

    return relax
