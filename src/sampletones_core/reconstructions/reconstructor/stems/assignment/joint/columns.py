from dataclasses import dataclass
from typing import Final, List, Mapping, Sequence, Set, Tuple

import numpy as np

from sampletones_core.constants.enums import GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher, RowsRequest, column_of
from sampletones_core.reconstructions.reconstructor.mix import FrameMix
from sampletones_shared.array import xp

from .batches import cheapest_row, split_by_group
from .catalog import KindCatalog
from .choice import ScoredCombination
from .hearing import FrameHearing
from .layout import StemLayout

VOLUME_NEIGHBORS: Final[int] = 4
SILENCE_ROOM: Final[int] = 1
LEAST_KEPT: Final[int] = 1

NoteRows = List[np.ndarray]


@dataclass(frozen=True)
class ChannelDraft:
    """One held channel's rows before the other proposed notes join them, and what it is scored beside.

    Attributes:
        place: The channel's place in the layout.
        options: What the choice plays on the channel, then the nearest volumes of its note.
        mix: What the stem's other channels sound in the frame, playing the choice.
        notes: The proposed notes of the channel's kind that no channel of that kind plays in the
            choice, in proposal order.
    """

    place: int
    options: List[int]
    mix: FrameMix
    notes: List[int]


class ChannelColumns:
    """Builds the column of every channel a stem holds, with the stem's other channels playing the frame's choice.

    A decoder of one channel at a time reads a channel's column with the other channels playing the
    choice, so each column offers the moves one channel may make from it:

    - what the choice plays on the channel, and for a sounding pulse or noise its ``VOLUME_NEIGHBORS``
      nearest volumes of the same note and timbre;
    - the best row of every proposed note of the channel's kind that no channel of that kind plays in
      the choice, by the spectral cost of the frame with the others sounding, cheapest first;
    - cut to leave ``SILENCE_ROOM`` of the ``width`` the decoder reads, keeping at least
      ``LEAST_KEPT``, then the channel's silence where the cut left it out.

    Each is scored by the full cost of the frame with the other channels sounding, as a column of one
    channel at a time is, and the column keeps the ``width`` best, a column wider than one with the
    silence among them (``column_of``). Every channel's rows are ranked together and scored together.

    Attributes:
        fragment: The stem's frame.
        layout: The stem's channels.
        catalogs: Each kind's rows.
        matcher: The candidate scoring machinery.
        hearing: How the frame hears each row.
        width: How many alternatives the decoder reads.
    """

    def __init__(
        self,
        fragment: Fragment,
        layout: StemLayout,
        catalogs: Mapping[GeneratorClassName, KindCatalog],
        matcher: FrameMatcher,
        hearing: FrameHearing,
        width: int,
    ) -> None:
        self.fragment = fragment
        self.layout = layout
        self.catalogs = catalogs
        self.matcher = matcher
        self.hearing = hearing
        self.width = width

    def columns(
        self,
        held: Sequence[int],
        winner: ScoredCombination,
        proposals: Mapping[GeneratorClassName, Sequence[int]],
    ) -> List[Column]:
        """Each held channel's alternatives with the stem's other channels playing ``winner``.

        Args:
            held: The places in the layout of the channels the stem holds.
            winner: The combination the frame's search chose.
            proposals: The rows proposed for each kind.

        Returns:
            One column per held channel, in ``held`` order, each best first and ``width`` long at most.
        """
        if not held:
            return []

        drafts = [self._drafted(index, winner, proposals) for index in held]
        requests = [self._request(draft, rows) for draft, rows in zip(drafts, self._alternates(drafts))]
        return [column_of(column, self.width) for column in self.matcher.score_requests(self.fragment, requests)]

    def _drafted(
        self, index: int, winner: ScoredCombination, proposals: Mapping[GeneratorClassName, Sequence[int]]
    ) -> ChannelDraft:
        """The channel's own options, the mix the others sound and the proposed notes left to it."""
        return ChannelDraft(
            place=index,
            options=self._own_options(index, winner),
            mix=self._others_mix(index, winner),
            notes=self._untaken_notes(index, winner, proposals),
        )

    def _own_options(self, index: int, winner: ScoredCombination) -> List[int]:
        """What ``winner`` plays on the channel, then, for a sounding channel playing levels, its nearest volumes."""
        slot = self.layout.slots[index]
        catalog = self.catalogs[slot.kind]
        head = winner.rows[index]
        options: List[int] = [head]
        if catalog.sounding(head) and slot.plays_levels:
            options.extend(catalog.neighbors(head, VOLUME_NEIGHBORS))

        return options

    def _others_mix(self, index: int, winner: ScoredCombination) -> FrameMix:
        """What the stem's other channels sound in the frame, playing ``winner``, on top of what the frame holds."""
        mix = self.hearing.empty_mix(self.fragment)
        for position, contribution in enumerate(winner.contributions):
            if position != index and contribution is not None:
                mix = mix.added(contribution)

        return mix

    def _untaken_notes(
        self, index: int, winner: ScoredCombination, proposals: Mapping[GeneratorClassName, Sequence[int]]
    ) -> List[int]:
        """The notes proposed for the channel's kind that no channel of the kind plays in ``winner``, each once."""
        kind = self.layout.slots[index].kind
        catalog = self.catalogs[kind]
        taken = self._taken_notes(kind, winner)
        proposed = (int(catalog.notes[row]) for row in proposals.get(kind, ()))
        return list(dict.fromkeys(note for note in proposed if note not in taken))

    def _taken_notes(self, kind: GeneratorClassName, winner: ScoredCombination) -> Set[int]:
        """The notes ``winner`` sounds on the stem's channels of ``kind``."""
        catalog = self.catalogs[kind]
        return {
            int(catalog.notes[row])
            for slot, row in zip(self.layout.slots, winner.rows)
            if slot.kind == kind and catalog.sounding(row)
        }

    def _alternates(self, drafts: Sequence[ChannelDraft]) -> List[List[int]]:
        """Each channel's best row of every note left to it, with its mix sounding, cheapest first.

        A note's best row is its cheapest, the earlier of equally cheap ones; notes whose best rows
        cost alike stand in row order.
        """
        rows_by_draft = [self._note_rows(draft) for draft in drafts]
        every_note = [rows for note_rows in rows_by_draft for rows in note_rows]
        if not every_note:
            return [[] for _ in drafts]

        stacks = [
            draft.mix.power + self.hearing.powers(draft.place, rows)
            for draft, note_rows in zip(drafts, rows_by_draft)
            for rows in note_rows
        ]
        costs = iter(split_by_group(self._spectral_costs(np.concatenate(stacks)), every_note))
        alternates: List[List[int]] = []
        for note_rows in rows_by_draft:
            best: List[Tuple[float, int]] = []
            for rows in note_rows:
                note_costs = next(costs)
                best.append((float(note_costs.min()), cheapest_row(rows, note_costs)))

            alternates.append([row for _, row in sorted(best)])

        return alternates

    def _note_rows(self, draft: ChannelDraft) -> NoteRows:
        """Every row of each note left to the channel, note by note."""
        catalog = self.catalogs[self.layout.slots[draft.place].kind]
        return [catalog.rows_of(note) for note in draft.notes]

    def _spectral_costs(self, powers: np.ndarray) -> np.ndarray:
        """The spectral cost of the frame with each row of ``powers`` sounding."""
        features = self.matcher.candidate_provider.features_of(xp.asarray(powers))
        return self.matcher.scorer.spectral_costs(self.fragment, features)

    def _request(self, draft: ChannelDraft, alternates: Sequence[int]) -> RowsRequest:
        """The channel's rows to score beside its mix: its options and alternates cut to the width, and its silence."""
        slot = self.layout.slots[draft.place]
        catalog = self.catalogs[slot.kind]
        kept = max(self.width - SILENCE_ROOM, LEAST_KEPT)
        options = list(dict.fromkeys([*draft.options, *alternates]))[:kept]
        if catalog.silence not in options:
            options.append(catalog.silence)

        return RowsRequest(
            generator=catalog.generator,
            mix=draft.mix,
            rows=tuple(options),
            powers=self.hearing.powers(draft.place, options),
            drive=slot.drive,
        )
