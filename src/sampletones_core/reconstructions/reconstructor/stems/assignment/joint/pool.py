from dataclasses import replace
from typing import Dict, List, Mapping, Sequence, Tuple

from sampletones_core.constants.algorithm import RESTING_FRAME_COST
from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions.reconstructor.contribution import Contribution
from sampletones_core.reconstructions.reconstructor.decoder.base import PooledCombination
from sampletones_core.reconstructions.reconstructor.matching import Column, ScoredCandidate
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import resting, silent_contribution
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool

from .catalog import KindCatalog
from .choice import ScoredCombination
from .layout import StemLayout

Played = Tuple[InstructionUnion, ...]


def sounding_pool(
    fragment: Fragment,
    layout: StemLayout,
    combinations: Sequence[ScoredCombination],
    columns: Mapping[int, Column],
    catalogs: Mapping[GeneratorClassName, KindCatalog],
) -> StemPool:
    """The stem's pool in a sounding frame: its combinations, the choice moved one channel at a time, every order.

    A column scores each of its channel's alternatives at the full cost of the frame with the other
    channels playing the choice, which is the cost of the choice with that one channel moved. So the
    pool holds every alternative of every column as such a combination, and a path may take any move
    a decoder of one channel at a time could. A pulse line keeps to its channel across frames only where
    the path may take either order, so each combination also stands in every order within each group of
    the stem's channels, which sound the same (``StemLayout.orders``). A combination reads once, by what
    its channels play, at the cost it was first pooled with: the frame's combinations in their order,
    then the moves column by column.

    Args:
        fragment: The stem's frame.
        layout: The stem's channels.
        combinations: The combinations the frame pooled, each once, the choice first.
        columns: The column of every channel the stem holds, keyed by its place in the layout.
        catalogs: Each kind's rows.

    Returns:
        The pool, the choice first.
    """
    silence = silent_contribution(fragment)
    pooled = [_pooled(layout, combination, catalogs, silence) for combination in combinations]
    arranged: Dict[Played, PooledCombination] = {}
    for combination in [*pooled, *_moved(pooled[0], columns)]:
        for candidates in layout.orders(combination.candidates):
            ordered = replace(combination, candidates=candidates)
            arranged.setdefault(_played(ordered), ordered)

    return StemPool(
        stem_id=layout.stem_id,
        channel_names=_channel_names(layout),
        combinations=tuple(arranged.values()),
    )


def resting_pool(fragment: Fragment, layout: StemLayout, channels: Dict[ChannelName, GeneratorUnion]) -> StemPool:
    """The stem's pool in a frame it leaves silent: every channel resting, the one combination there is."""
    rests = resting(_channel_names(layout), channels, fragment)
    return StemPool(
        stem_id=layout.stem_id,
        channel_names=_channel_names(layout),
        combinations=(PooledCombination(candidates=tuple(rest.column[0] for rest in rests), cost=RESTING_FRAME_COST),),
    )


def _moved(choice: PooledCombination, columns: Mapping[int, Column]) -> List[PooledCombination]:
    """``choice`` with one channel playing each alternative of its column, column by column."""
    moves: List[PooledCombination] = []
    for index, column in columns.items():
        for candidate in column:
            moves.append(_moved_to(choice, index, candidate))

    return moves


def _moved_to(choice: PooledCombination, index: int, candidate: ScoredCandidate) -> PooledCombination:
    """``choice`` with channel ``index`` playing ``candidate``, every channel at the candidate's cost.

    The column scored ``candidate`` with the other channels playing the choice, so its cost is the
    cost of the whole combination.
    """
    candidates = [replace(kept, cost=candidate.cost) for kept in choice.candidates]
    candidates[index] = candidate
    return PooledCombination(candidates=tuple(candidates), cost=candidate.cost)


def _pooled(
    layout: StemLayout,
    combination: ScoredCombination,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    silence: Contribution,
) -> PooledCombination:
    """``combination`` as each channel's candidate, every one at what the frame's choice weighs it by.

    A silent channel adds the frame's silence.
    """
    candidates: List[ScoredCandidate] = []
    for slot, row, contribution in zip(layout.slots, combination.rows, combination.contributions):
        candidates.append(
            ScoredCandidate(
                instruction=catalogs[slot.kind].instructions[row],
                cost=combination.weighed,
                contribution=silence if contribution is None else contribution,
            )
        )

    return PooledCombination(candidates=tuple(candidates), cost=combination.weighed)


def _played(combination: PooledCombination) -> Played:
    """What every channel of ``combination`` plays, which is what a combination reads once by."""
    return tuple(candidate.instruction for candidate in combination.candidates)


def _channel_names(layout: StemLayout) -> Tuple[ChannelName, ...]:
    """The stem's channels, in the order every combination of its pool lists them."""
    return tuple(slot.channel_name for slot in layout.slots)
