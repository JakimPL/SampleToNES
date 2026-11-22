import itertools
from typing import Dict, Final, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from sampletones_core.constants.enums import ChannelName, GeneratorClassName
from sampletones_core.fft import Fragment
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.decoder.base import Streams
from sampletones_core.reconstructions.reconstructor.matching import FrameMatcher
from sampletones_core.reconstructions.reconstructor.stems.assignment.rests import resting, sounding_stems
from sampletones_core.reconstructions.reconstructor.stems.assignment.validation import validate_stems_config
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.models.choice import StemChoice
from sampletones_core.reconstructions.reconstructor.stems.models.frame_assignment import StemFrameAssignment
from sampletones_core.reconstructions.reconstructor.stems.models.pool import StemPool
from sampletones_core.reconstructions.reconstructor.window.surroundings import ChannelLine, ChannelSurroundings
from sampletones_shared.array import to_numpy

from .catalog import KindCatalog
from .choice import CombinationJudge, ScoredCombination, rearranged
from .columns import channel_columns
from .combinations import CombinationSearch, Rows
from .continuity import ChannelContinuity, StemContinuity
from .fit import FitTarget
from .hearing import FrameHearing, SequenceHearing, SteadyHearing
from .layout import StemLayout, separate_layouts
from .pool import resting_pool, sounding_pool
from .proposals import NoteDictionary, proposed_rows

UNVOICED_DISTANCE: Final[float] = 24.0

PulseNotes = Tuple[Optional[int], ...]


class JointAssigner:
    """Assigns a recording's frames by fitting every note at once and choosing among complete combinations.

    Each sounding stem's frame is read on its own channels:

    1. Every note the stem's channels may sound is fitted to the frame at once, and the strongest
       notes of each kind become the frame's proposals.
    2. Every combination of the proposals the stem may sound together is fitted, the pulse and noise
       levels free and the triangle at its one level, and the best are moved onto the library's
       rows one channel at a time.
    3. The full criterion chooses among the cheapest, and each channel's column lists its
       alternatives with the other channels playing the choice, which is what a decoder of one channel
       at a time reads. The stem's pool holds the choice with every set of its channels silenced, the
       cheapest with one channel silenced, the choice with one channel moved to each alternative of its
       column and the choice of the frame before, which is what a decoder over combinations reads.

    Every decision between notes compares complete mixes, so a note that only covers other notes'
    partials loses to the notes themselves. The two pulses are handed to the channels that keep each
    nearest the note it played the frame before, so a held line stays on its channel.

    A frame is first heard alone, each note as if held through the whole analysis window. Once the
    recording is decoded, a frame may be assigned again among the notes its neighbors play: what
    they leave in its window is a fixed part of every mix, and a note extending a neighbor's note
    adds to it as one note held across the frames. Its choice may then also pay for breaking with
    what the frames beside it play.
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
        generators: Dict[GeneratorClassName, GeneratorUnion] = {}
        for layout in self.layouts:
            for slot in layout.slots:
                generators.setdefault(slot.kind, channels[slot.channel_name])
        self.catalogs = {
            kind: KindCatalog.build(matcher.candidate_provider, generator) for kind, generator in generators.items()
        }
        self.dictionaries = {layout.stem_id: NoteDictionary.of(layout, self.catalogs) for layout in self.layouts}
        self.weights = np.asarray(to_numpy(matcher.scorer.criterion.weights), dtype=np.float64).reshape(-1)
        self.previous: Dict[int, Optional[PulseNotes]] = {layout.stem_id: None for layout in self.layouts}
        self.previous_rows: Dict[int, Optional[Rows]] = {layout.stem_id: None for layout in self.layouts}

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
            {layout.stem_id: StemContinuity.free(layout) for layout in self.layouts},
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
        continuities = {
            layout.stem_id: StemContinuity(channels=tuple(continuity[slot.channel_name] for slot in layout.slots))
            for layout in self.layouts
        }
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
            for slot in layout.slots:
                catalog = self.catalogs[slot.kind]
                rows = [catalog.rows_by_instruction[candidate.instruction] for candidate in streams[slot.channel_name]]
                lines[slot.channel_name] = ChannelLine(
                    keys=[catalog.key(row) for row in rows],
                    powers=catalog.powers[rows] / slot.drive**2,
                    instructions=[catalog.instructions[row] for row in rows],
                    coherent=slot.kind != GeneratorClassName.NOISE_GENERATOR,
                )

        return lines

    def settle(self, lines: Mapping[ChannelName, ChannelLine], frame: int, assignment: StemFrameAssignment) -> None:
        """Settles every stem channel's line at ``frame`` on what ``assignment`` heads it with, silence where it rests.

        Args:
            lines: Every stem channel's line, keyed by channel name.
            frame: The frame ``assignment`` assigns.
            assignment: The frame's assignment.
        """
        heads = {choice.channel_name: choice.instruction for choice in assignment.choices}
        for layout in self.layouts:
            for slot in layout.slots:
                catalog = self.catalogs[slot.kind]
                head = heads.get(slot.channel_name)
                row = catalog.silence if head is None else catalog.rows_by_instruction[head]
                lines[slot.channel_name].settle(
                    frame, catalog.key(row), catalog.powers[row] / slot.drive**2, catalog.instructions[row]
                )

    def _assigned(
        self,
        fragments: Dict[int, Fragment],
        hearings: Mapping[int, FrameHearing],
        continuities: Mapping[int, StemContinuity],
    ) -> StemFrameAssignment:
        """Assigns one frame, each sounding stem's frame heard as ``hearings`` hears it and kept to ``continuities``."""
        sounding = sounding_stems(fragments)
        choices: List[StemChoice] = []
        rested: List[ChannelName] = []
        pools: List[StemPool] = []
        for layout in self.layouts:
            if not layout.slots:
                continue

            fragment = fragments[layout.stem_id]
            if layout.stem_id in sounding:
                held, idle, pool = self._stem_frame(
                    layout, fragment, hearings[layout.stem_id], continuities[layout.stem_id]
                )
                choices.extend(held)
                rested.extend(idle)
            else:
                self.previous[layout.stem_id] = None
                self.previous_rows[layout.stem_id] = None
                rested.extend(slot.channel_name for slot in layout.slots)
                pool = resting_pool(fragment, layout, self.channels)
            pools.append(pool)

        ordered = [name for name in ChannelName.items() if name in rested]
        return StemFrameAssignment(
            choices=tuple(choices),
            rests=resting(ordered, self.channels, next(iter(fragments.values()))) if ordered else (),
            pools=tuple(pools),
        )

    def _stem_frame(
        self, layout: StemLayout, fragment: Fragment, hearing: FrameHearing, continuity: StemContinuity
    ) -> Tuple[List[StemChoice], List[ChannelName], StemPool]:
        """One stem's channels in one frame: those it holds, each with its column, those left resting and its pool."""
        target = FitTarget.of(fragment, self.matcher.scorer.criterion)
        proposals = proposed_rows(
            fragment, target, layout, self.dictionaries[layout.stem_id], self.catalogs, self.matcher, hearing
        )
        search = CombinationSearch(fragment, target, layout, self.catalogs, self.matcher, hearing)
        refined = search.refined(search.fitted(proposals))
        judge = CombinationJudge(fragment, layout, self.catalogs, self.matcher, self.weights, hearing, continuity)
        finalists = judge.finalists([combination.rows for combination in refined])
        winner = self._ordered(layout, judge.best(search, finalists))
        pooled = judge.pooled(search, finalists, winner, self.previous_rows[layout.stem_id])
        self.previous_rows[layout.stem_id] = winner.rows

        held = self._held(layout, winner)
        columns = [
            continuity.charged(layout, self.catalogs, index, column, winner.rows)
            for index, column in zip(
                held,
                channel_columns(
                    fragment, layout, held, winner, proposals, self.catalogs, self.matcher, self.width, hearing
                ),
            )
        ]
        choices = [
            StemChoice(stem_id=layout.stem_id, channel_name=layout.slots[index].channel_name, column=column)
            for index, column in zip(held, columns)
        ]
        idle = [slot.channel_name for index, slot in enumerate(layout.slots) if index not in held]
        pool = sounding_pool(fragment, layout, pooled, dict(zip(held, columns)), self.catalogs)
        return choices, idle, pool

    def _held(self, layout: StemLayout, winner: ScoredCombination) -> List[int]:
        """The channels the stem holds: those the winner sounds, then silent ones up to the stem's count."""
        sounding = [
            index
            for index, (slot, row) in enumerate(zip(layout.slots, winner.rows))
            if self.catalogs[slot.kind].sounding(row)
        ]
        silent = [index for index in range(len(layout.slots)) if index not in sounding]
        return sorted([*sounding, *silent[: max(layout.cap - len(sounding), 0)]])

    def _ordered(self, layout: StemLayout, winner: ScoredCombination) -> ScoredCombination:
        """The winner with its pulses on the channels that keep each nearest the note it played a frame before.

        Pulses the stem drives alike sound the same on either channel, so they are free to swap; with
        no frame before, the sounding pulses come first.
        """
        pulses = [index for index, slot in enumerate(layout.slots) if slot.kind == GeneratorClassName.PULSE_GENERATOR]
        catalog = self.catalogs.get(GeneratorClassName.PULSE_GENERATOR)
        if catalog is None or not pulses:
            return winner

        interchangeable = layout.interchangeable_pulses
        if interchangeable:
            previous = self.previous[layout.stem_id]
            winner = min(
                (rearranged(winner, interchangeable, order) for order in itertools.permutations(interchangeable)),
                key=lambda arranged: _distance([catalog.note_name(arranged.rows[index]) for index in pulses], previous),
            )

        self.previous[layout.stem_id] = tuple(catalog.note_name(winner.rows[index]) for index in pulses)
        return winner


def _distance(notes: Sequence[Optional[int]], previous: Optional[PulseNotes]) -> float:
    """How far pulses playing ``notes`` move from ``previous``; with nothing before, a later sounding pulse costs."""
    if previous is None:
        return float(sum(position for position, note in enumerate(notes) if note is not None))

    total = 0.0
    for now, before in zip(notes, previous):
        if now is None and before is None:
            continue
        total += UNVOICED_DISTANCE if now is None or before is None else abs(now - before)

    return total
