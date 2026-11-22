from dataclasses import dataclass
from typing import Final, List, Mapping, Sequence, Set, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher, RowsRequest, column_of
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_shared.array import xp

from .catalog import KindCatalog
from .choice import ScoredCombination
from .hearing import FrameHearing
from .layout import StemLayout

VOLUME_NEIGHBORS: Final[int] = 4


@dataclass(frozen=True)
class _ChannelDraft:
    """One channel's rows before the other proposed notes join them: its head, its neighbors and its mix."""

    index: int
    options: List[int]
    mix: FrameMix
    notes: List[int]


def channel_columns(
    fragment: Fragment,
    layout: StemLayout,
    held: Sequence[int],
    winner: ScoredCombination,
    proposals: Mapping[GeneratorClassName, Sequence[int]],
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
    width: int,
    hearing: FrameHearing,
) -> List[Column]:
    """Each held channel's alternatives with the stem's other channels playing the winning combination.

    A column holds what the winner plays on the channel, the same note at its nearest volumes, the
    best row of every other note proposed for the channel's kind that no channel of the winner plays,
    and the channel's silence. Each is scored by the full cost of the frame with the other channels
    sounding, as a column of one channel at a time is, so the decoder reads it the same way. Every
    channel's rows are ranked and scored together.

    Args:
        fragment: The stem's frame.
        layout: The stem's channels.
        held: The places in the layout of the channels the stem holds.
        winner: The combination the frame's search chose.
        proposals: The rows proposed for each kind.
        catalogs: Each kind's rows.
        matcher: The candidate scoring machinery.
        width: How many alternatives the decoder reads.
        hearing: How the frame hears each row.

    Returns:
        One column per held channel, in ``held`` order, each best first and ``width`` long at most.
    """
    if not held:
        return []

    drafts = [_drafted(fragment, layout, index, winner, proposals, catalogs, hearing) for index in held]
    alternates = _alternates(fragment, layout, drafts, catalogs, matcher, hearing)
    requests: List[RowsRequest] = []
    for draft, rows in zip(drafts, alternates):
        slot = layout.slots[draft.index]
        catalog = catalogs[slot.kind]
        options = list(dict.fromkeys([*draft.options, *rows]))[: max(width - 1, 1)]
        if catalog.silence not in options:
            options.append(catalog.silence)
        requests.append(
            RowsRequest(
                generator=catalog.generator,
                mix=draft.mix,
                rows=tuple(options),
                powers=hearing.powers(draft.index, options),
                drive=slot.drive,
            )
        )

    return [column_of(column, width) for column in matcher.score_requests(fragment, requests)]


def _drafted(
    fragment: Fragment,
    layout: StemLayout,
    index: int,
    winner: ScoredCombination,
    proposals: Mapping[GeneratorClassName, Sequence[int]],
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    hearing: FrameHearing,
) -> _ChannelDraft:
    """The channel's head and its nearest volumes, the mix the others sound and the proposed notes left untaken."""
    slot = layout.slots[index]
    catalog = catalogs[slot.kind]
    others = [
        contribution
        for position, contribution in enumerate(winner.contributions)
        if position != index and contribution is not None
    ]
    head = winner.rows[index]
    options: List[int] = [head]
    if catalog.sounding(head) and slot.kind != GeneratorClassName.TRIANGLE_GENERATOR:
        options.extend(catalog.neighbors(head, VOLUME_NEIGHBORS))

    taken = _taken_notes(layout, index, winner, catalogs)
    notes = list(
        dict.fromkeys(
            int(catalog.notes[row]) for row in proposals.get(slot.kind, ()) if int(catalog.notes[row]) not in taken
        )
    )
    mix = hearing.empty_mix(fragment)
    for contribution in others:
        mix = mix.added(contribution)

    return _ChannelDraft(index=index, options=options, mix=mix, notes=notes)


def _taken_notes(
    layout: StemLayout,
    index: int,
    winner: ScoredCombination,
    catalogs: Mapping[GeneratorClassName, KindCatalog],
) -> Set[int]:
    """The notes the winner plays on the channel and on the stem's other channels of its kind."""
    kind = layout.slots[index].kind
    catalog = catalogs[kind]
    return {
        int(catalog.notes[row])
        for slot, row in zip(layout.slots, winner.rows)
        if slot.kind == kind and catalog.sounding(row)
    }


def _alternates(
    fragment: Fragment,
    layout: StemLayout,
    drafts: Sequence[_ChannelDraft],
    catalogs: Mapping[GeneratorClassName, KindCatalog],
    matcher: FrameMatcher,
    hearing: FrameHearing,
) -> List[List[int]]:
    """Each channel's best row of every proposed note left untaken, with its mix sounding, cheapest first."""
    stacks: List[np.ndarray] = []
    groups: List[Tuple[int, List[np.ndarray]]] = []
    for position, draft in enumerate(drafts):
        catalog = catalogs[layout.slots[draft.index].kind]
        rows_by_note = [catalog.rows_of(note) for note in draft.notes]
        for rows in rows_by_note:
            stacks.append(draft.mix.power + hearing.powers(draft.index, rows))
        groups.append((position, rows_by_note))

    alternates: List[List[int]] = [[] for _ in drafts]
    if not stacks:
        return alternates

    features = matcher.candidate_provider.features_of(xp.asarray(np.concatenate(stacks)))
    costs = matcher.scorer.spectral_costs(fragment, features)
    start = 0
    for position, rows_by_note in groups:
        best: List[Tuple[float, int]] = []
        for rows in rows_by_note:
            note_costs = costs[start : start + len(rows)]
            best.append((float(note_costs.min()), int(rows[int(np.argmin(note_costs))])))
            start += len(rows)
        alternates[position] = [row for _, row in sorted(best)]

    return alternates
