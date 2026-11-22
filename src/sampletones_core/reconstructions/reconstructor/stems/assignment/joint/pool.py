import itertools
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
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import resting
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool

from .catalog import KindCatalog
from .choice import ScoredCombination
from .layout import StemLayout


def sounding_pool(
    fragment: Fragment,
    layout: StemLayout,
    combinations: Sequence[ScoredCombination],
    columns: Mapping[int, Column],
    catalogs: Mapping[GeneratorClassName, KindCatalog],
) -> StemPool:
    """The stem's pool in a sounding frame: its combinations, the choice moved one channel at a time, both pulse orders.

    A column scores each of its channel's alternatives at the full cost of the frame with the other
    channels playing the choice, which is the cost of the choice with that one channel moved. So the
    pool holds every alternative of every column as such a combination, and a path may take any move
    a decoder of one channel at a time could. A pulse line keeps to its channel across frames only where
    the path may take either order, so each combination also stands in every order its pulses sound the
    same in. A combination reads once, at the cost it was first pooled with.

    Args:
        fragment: The stem's frame.
        layout: The stem's channels.
        combinations: The combinations the frame pooled, each once, the choice first.
        columns: The column of every channel the stem holds, keyed by its place in the layout.
        catalogs: Each kind's rows.

    Returns:
        The pool, the choice first.
    """
    silence = Contribution.silence(len(fragment.feature.values), fragment.audio.shape[0])
    pooled = [_pooled(layout, combination, catalogs, silence) for combination in combinations]
    arranged: Dict[Tuple[InstructionUnion, ...], PooledCombination] = {}
    for combination in [*pooled, *_moved(pooled[0], columns)]:
        for ordered in _orders(layout, combination):
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
    """``choice`` with one channel playing each alternative of its column, every channel at the column's cost."""
    return [
        PooledCombination(
            candidates=tuple(
                candidate if position == index else replace(kept, cost=candidate.cost)
                for position, kept in enumerate(choice.candidates)
            ),
            cost=candidate.cost,
        )
        for index, column in columns.items()
        for candidate in column
    ]


def _orders(layout: StemLayout, combination: PooledCombination) -> List[PooledCombination]:
    """``combination`` in every order of the stem's interchangeable pulses, its own order first."""
    pulses = layout.interchangeable_pulses
    orders: List[PooledCombination] = []
    for order in itertools.permutations(pulses):
        candidates = list(combination.candidates)
        for target, source in zip(pulses, order):
            candidates[target] = combination.candidates[source]
        orders.append(replace(combination, candidates=tuple(candidates)))

    return orders


def _pooled(
    layout: StemLayout,
    combination: ScoredCombination,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    silence: Contribution,
) -> PooledCombination:
    """``combination`` as each channel's candidate, every one at what the frame's choice weighs it by."""
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


def _played(combination: PooledCombination) -> Tuple[InstructionUnion, ...]:
    return tuple(candidate.instruction for candidate in combination.candidates)


def _channel_names(layout: StemLayout) -> Tuple[ChannelName, ...]:
    return tuple(slot.channel_name for slot in layout.slots)
