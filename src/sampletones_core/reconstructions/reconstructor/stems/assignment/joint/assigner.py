from dataclasses import dataclass, replace
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.candidates import CandidateProvider
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.matching import Column, FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import resting, sounding_stems
from sampletones_core.reconstructions.reconstructor.stems.assignment.validation import validate_stems_config
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool
from sampletones_core.reconstructions.reconstructor.window.surroundings import ChannelLine, ChannelSurroundings
from sampletones_shared.array import to_numpy

from .catalog import KindCatalog
from .choice import CombinationJudge, ScoredCombination
from .columns import ChannelColumns
from .combinations import CombinationSearch, Rows
from .continuity import ChannelContinuity, StemContinuity
from .fit import FitTarget
from .hearing import FrameHearing, SequenceHearing, SteadyHearing, library_powers
from .layout import StemLayout, separate_layouts
from .pool import resting_pool, sounding_pool
from .proposals import NoteDictionary, proposed_rows

UNVOICED_DISTANCE: Final[float] = 24.0

PulseNotes = Tuple[Optional[int], ...]


@dataclass(frozen=True)
class PulseHandover:
    """Hands a frame's pulse notes to the stem's pulse channels, so a line a pulse holds stays on its channel.

    Pulses the stem drives alike sound the same on either channel, so the winner may stand in any
    order of them. The handover keeps the order moving the pulses least from the notes they played
    the frame before: a pulse moves by the semitones between its two notes, and a pulse starting or
    falling silent moves ``UNVOICED_DISTANCE`` semitones. With no frame before, a sounding pulse
    stands as early in the layout as it can. Of orders moving alike, the earlier in
    ``StemLayout.pulse_orders`` stands, the winner's own order first.

    Attributes:
        layout: The stem's channels, whose pulses are interchangeable.
        catalog: The pulse rows.
    """

    layout: StemLayout
    catalog: KindCatalog

    def ordered(self, winner: ScoredCombination, previous: Optional[Rows]) -> ScoredCombination:
        """``winner`` in the order of its pulses that moves them least from ``previous``, ``None`` after a rest."""
        before = None if previous is None else self._notes(previous)
        arrangements = self._arrangements(winner)
        moves = [self.moved(self._notes(arranged.rows), before) for arranged in arrangements]
        return arrangements[moves.index(min(moves))]

    def _arrangements(self, winner: ScoredCombination) -> List[ScoredCombination]:
        """``winner`` in every order of its interchangeable pulses, each row moving with what it adds, its own first."""
        orders = zip(self.layout.pulse_orders(winner.rows), self.layout.pulse_orders(winner.contributions))
        return [replace(winner, rows=rows, contributions=contributions) for rows, contributions in orders]

    @staticmethod
    def moved(notes: PulseNotes, before: Optional[PulseNotes]) -> float:
        """How far pulses playing ``notes`` move from playing ``before``, ``None`` with no frame before.

        With no frame before, each sounding pulse costs its place among the pulses, so the sounding
        ones come first.
        """
        if before is None:
            return float(sum(position for position, note in enumerate(notes) if note is not None))

        total = 0.0
        for now, then in zip(notes, before):
            if now is None and then is None:
                continue

            total += UNVOICED_DISTANCE if now is None or then is None else abs(now - then)

        return total

    def _notes(self, rows: Rows) -> PulseNotes:
        """The note each interchangeable pulse plays in ``rows``, ``None`` for a silent one."""
        return tuple(self.catalog.note_name(rows[place]) for place in self.layout.interchangeable_pulses)


@dataclass(frozen=True)
class StemAnswer:
    """One stem's part of a frame's assignment.

    Attributes:
        choices: The channels the stem holds, each with its column.
        resting: The stem's channels it leaves resting.
        pool: The stem's whole combinations.
    """

    choices: List[StemChoice]
    resting: List[ChannelName]
    pool: StemPool


class JointAssigner:
    """Assigns a recording's frames by fitting every note at once and choosing among complete combinations.

    Each sounding stem's frame is read on its own channels:

    1. Every note the stem's channels may sound is fitted to the frame at once, and the strongest
       notes of each kind become the frame's proposals.
    2. Every combination of the proposals the stem may sound together is fitted, the pulse and noise
       levels free and the triangle at its one level, and the best are moved onto the library's
       rows one channel at a time.
    3. The full criterion chooses among the cheapest (``CombinationJudge``).
    4. The stem holds the channels the choice sounds, and silent ones up to the stem's count, so a
       decoder of one channel at a time, which may sound every channel held, keeps within the count.
       Each held channel's column lists its alternatives with the other channels playing the choice
       (``ChannelColumns``), which is what such a decoder reads. The stem's pool holds the whole
       combinations a decoder over combinations reads (``CombinationJudge.pooled``, ``sounding_pool``).

    Every decision between notes compares complete mixes, so a note that only covers other notes'
    partials loses to the notes themselves. The pulses are handed to the channels that keep each
    nearest the note it played the frame before (``PulseHandover``), so a held line stays on its
    channel. The assigner remembers each stem's previous choice for that and for the pool, and a
    frame the stem leaves silent clears it.

    A frame is first heard alone, each note as if held through the whole analysis window. Once the
    recording is decoded, a frame may be assigned again among the notes its neighbors play
    (``assign_beside``): what they leave in its window is a fixed part of every mix, and a note
    extending a neighbor's note adds to it as one note held across the frames. Its choice, columns
    and pool may then also pay for breaking with what the frames beside it play.
    """

    def __init__(
        self,
        stems_config: StemsConfig,
        channels: Dict[ChannelName, GeneratorUnion],
        matcher: FrameMatcher,
        lattice_width: int,
    ) -> None:
        """Builds the assigner for one recording.

        Raises:
            ValueError: If a stem allows a channel the run has no generator for, or two stems may
                occupy the same channel.
        """
        validate_stems_config(stems_config, channels)
        self.layouts = separate_layouts(stems_config, channels)
        self.channels = channels
        self.matcher = matcher
        self.width = lattice_width
        self.catalogs = self._kind_catalogs(self.layouts, channels, matcher.candidate_provider)
        self.dictionaries = {layout.stem_id: NoteDictionary.of(layout, self.catalogs) for layout in self.layouts}
        self.weights = np.asarray(to_numpy(matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
        self.previous: Dict[int, Optional[Rows]] = {layout.stem_id: None for layout in self.layouts}

    def assign(self, fragments: Dict[int, Fragment]) -> StemFrameAssignment:
        """Assigns one frame heard alone: every sounding stem's channels from its own frame, the rest resting.

        Args:
            fragments: This frame of every stem, keyed by stem id.

        Returns:
            The channels each stem holds, the channels left resting and every stem's pool.
        """
        bins = len(next(iter(fragments.values())).feature.values)
        return self._assigned(
            fragments,
            {
                layout.stem_id: SteadyHearing(layout=layout, catalogs=self.catalogs, bins=bins)
                for layout in self.layouts
            },
            {layout.stem_id: StemContinuity.free(layout, self.catalogs) for layout in self.layouts},
        )

    def assign_beside(
        self,
        fragments: Dict[int, Fragment],
        surroundings: Mapping[ChannelName, ChannelSurroundings],
        continuity: Mapping[ChannelName, ChannelContinuity],
    ) -> StemFrameAssignment:
        """Assigns one frame among the notes its neighbors were decoded to play.

        Args:
            fragments: This frame of every stem, keyed by stem id.
            surroundings: What every channel holds around the frame.
            continuity: What every channel plays beside the frame, and what the frame's choice pays
                to break with it.

        Returns:
            The channels each stem holds, the channels left resting and every stem's pool.
        """
        provider = self.matcher.candidate_provider
        hearings: Dict[int, FrameHearing] = {
            layout.stem_id: SequenceHearing.of(
                layout, self.catalogs, [surroundings[slot.channel_name] for slot in layout.slots], provider
            )
            for layout in self.layouts
            if layout.slots
        }
        continuities = {layout.stem_id: StemContinuity.of(layout, self.catalogs, continuity) for layout in self.layouts}
        return self._assigned(fragments, hearings, continuities)

    def lines(self, streams: Streams) -> Dict[ChannelName, ChannelLine]:
        """Every stem channel's decoded frames as the analysis hears them, at the drive the stem gives it.

        Args:
            streams: The decoded streams of the channels in play.

        Returns:
            Each channel's line, keyed by channel name.
        """
        lines: Dict[ChannelName, ChannelLine] = {}
        for layout in self.layouts:
            for place, slot in enumerate(layout.slots):
                catalog = self.catalogs[slot.kind]
                rows = [catalog.rows_by_instruction[candidate.instruction] for candidate in streams[slot.channel_name]]
                lines[slot.channel_name] = ChannelLine(
                    keys=[catalog.key(row) for row in rows],
                    powers=library_powers(layout, self.catalogs, place, rows),
                    instructions=[catalog.instructions[row] for row in rows],
                    coherent=slot.kind != GeneratorClassName.NOISE_GENERATOR,
                )

        return lines

    def settle(self, lines: Mapping[ChannelName, ChannelLine], frame: int, assignment: StemFrameAssignment) -> None:
        """Settles every stem channel's line at ``frame`` on its column's head in ``assignment``, silence if resting.

        Args:
            lines: Every stem channel's line, keyed by channel name.
            frame: The frame ``assignment`` assigns.
            assignment: The frame's assignment.
        """
        heads = {choice.channel_name: choice.instruction for choice in assignment.choices}
        for layout in self.layouts:
            for place, slot in enumerate(layout.slots):
                catalog = self.catalogs[slot.kind]
                head = heads.get(slot.channel_name)
                row = catalog.silence if head is None else catalog.rows_by_instruction[head]
                lines[slot.channel_name].settle(
                    frame,
                    catalog.key(row),
                    library_powers(layout, self.catalogs, place, [row])[0],
                    catalog.instructions[row],
                )

    @staticmethod
    def _kind_catalogs(
        layouts: Sequence[StemLayout], channels: Dict[ChannelName, GeneratorUnion], provider: CandidateProvider
    ) -> Dict[GeneratorClassName, KindCatalog]:
        """The rows of every kind a stem may sound, each read from the first channel of the kind a stem holds."""
        generators: Dict[GeneratorClassName, GeneratorUnion] = {}
        for layout in layouts:
            for slot in layout.slots:
                generators.setdefault(slot.kind, channels[slot.channel_name])

        return {kind: KindCatalog.build(provider, generator) for kind, generator in generators.items()}

    def _assigned(
        self,
        fragments: Dict[int, Fragment],
        hearings: Mapping[int, FrameHearing],
        continuities: Mapping[int, StemContinuity],
    ) -> StemFrameAssignment:
        """Assigns one frame, each sounding stem's frame heard as ``hearings`` hears it and kept to ``continuities``.

        The channels left resting stand in channel order.
        """
        sounding = sounding_stems(fragments)
        answers: List[StemAnswer] = []
        for layout in self.layouts:
            if not layout.slots:
                continue

            fragment = fragments[layout.stem_id]
            if layout.stem_id in sounding:
                answers.append(
                    self._sounding_stem(layout, fragment, hearings[layout.stem_id], continuities[layout.stem_id])
                )
            else:
                answers.append(self._silent_stem(layout, fragment))

        rested = {channel_name for answer in answers for channel_name in answer.resting}
        ordered = [name for name in ChannelName.items() if name in rested]
        return StemFrameAssignment(
            choices=tuple(choice for answer in answers for choice in answer.choices),
            rests=resting(ordered, self.channels, next(iter(fragments.values()))) if ordered else (),
            pools=tuple(answer.pool for answer in answers),
        )

    def _silent_stem(self, layout: StemLayout, fragment: Fragment) -> StemAnswer:
        """A stem's frame it leaves silent: every channel resting, and its previous choice cleared."""
        self.previous[layout.stem_id] = None
        return StemAnswer(
            choices=[],
            resting=[slot.channel_name for slot in layout.slots],
            pool=resting_pool(fragment, layout, self.channels),
        )

    def _sounding_stem(
        self, layout: StemLayout, fragment: Fragment, hearing: FrameHearing, continuity: StemContinuity
    ) -> StemAnswer:
        """One sounding stem's frame: the judge's choice, the channels it holds with their columns, and its pool."""
        target = FitTarget.of(fragment, self.matcher.scorer.criterion)
        proposals = proposed_rows(
            fragment, target, layout, self.dictionaries[layout.stem_id], self.catalogs, self.matcher, hearing
        )
        search = CombinationSearch(fragment, target, layout, self.catalogs, self.matcher, hearing)
        judge = CombinationJudge(fragment, layout, self.catalogs, self.matcher, self.weights, hearing, continuity)
        finalists = judge.finalists([combination.rows for combination in search.refined(search.fitted(proposals))])
        previous = self.previous[layout.stem_id]
        winner = self._handed_over(layout, judge.best(search, finalists), previous)
        pooled = judge.pooled(search, finalists, winner, previous)
        self.previous[layout.stem_id] = winner.rows

        held = self._held(layout, winner)
        built = ChannelColumns(fragment, layout, self.catalogs, self.matcher, hearing, self.width)
        columns = [
            continuity.charged(index, column, winner.rows)
            for index, column in zip(held, built.columns(held, winner, proposals))
        ]
        return StemAnswer(
            choices=self._choices(layout, held, columns),
            resting=[slot.channel_name for index, slot in enumerate(layout.slots) if index not in held],
            pool=sounding_pool(fragment, layout, pooled, dict(zip(held, columns)), self.catalogs),
        )

    def _handed_over(
        self, layout: StemLayout, winner: ScoredCombination, previous: Optional[Rows]
    ) -> ScoredCombination:
        """The winner with its pulses handed to their channels, where the stem's pulses are interchangeable."""
        if not layout.interchangeable_pulses:
            return winner

        return PulseHandover(layout=layout, catalog=self.catalogs[GeneratorClassName.PULSE_GENERATOR]).ordered(
            winner, previous
        )

    def _held(self, layout: StemLayout, winner: ScoredCombination) -> List[int]:
        """The places of the channels the stem holds, in layout order.

        These are the channels the winner sounds, then its silent ones in layout order up to the
        stem's count.
        """
        sounding = [
            index
            for index, (slot, row) in enumerate(zip(layout.slots, winner.rows))
            if self.catalogs[slot.kind].sounding(row)
        ]
        silent = [index for index in range(len(layout.slots)) if index not in sounding]
        return sorted([*sounding, *silent[: max(layout.cap - len(sounding), 0)]])

    @staticmethod
    def _choices(layout: StemLayout, held: Sequence[int], columns: Sequence[Column]) -> List[StemChoice]:
        """The stem's hold on each channel at ``held``, with its column."""
        return [
            StemChoice(stem_id=layout.stem_id, channel_name=layout.slots[index].channel_name, column=column)
            for index, column in zip(held, columns)
        ]
