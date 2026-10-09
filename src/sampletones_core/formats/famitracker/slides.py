from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Final, FrozenSet, List, Mapping, Set, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.transpose import PatternCell, PitchWalk, Repitch, SoundingNote
from sampletones_core.exporters.skipped import SkippedRow, SkipReason
from sampletones_core.formats.famitracker.specification.patterns import (
    FASTEST_SLIDE_SPEED,
    MAX_SLIDE_SEMITONES,
    SLIDE_SPEED_SHIFT,
    EffectId,
)
from sampletones_core.formats.famitracker.targets import RowTargets

NO_SLIDE: Final[int] = 0

SlideEffect = Tuple[int, int]


def slide_effect(semitones: int) -> SlideEffect:
    """The effect column moving a channel's note by ``semitones`` at the highest speed: ``Qxy`` up, ``Rxy`` down.

    Args:
        semitones: How far the note moves, within ``MAX_SLIDE_SEMITONES`` either way.

    Returns:
        SlideEffect: The effect number and its parameter.
    """
    effect = EffectId.SLIDE_UP if semitones > NO_SLIDE else EffectId.SLIDE_DOWN
    return int(effect), (FASTEST_SLIDE_SPEED << SLIDE_SPEED_SHIFT) | abs(semitones)


@dataclass
class _ChannelSlides:
    """One channel's pass through the notes transpose rows move, deciding each pattern cell once.

    A module stores a pattern once for every frame that plays it, so a cell carries one slide
    wherever the order reaches it. The first frame reaching a cell while a note sounds decides it,
    and a later frame needing another slide there is reported.
    """

    channel_name: ChannelName
    targets: RowTargets
    decided: Dict[PatternCell, int] = field(default_factory=dict)
    skipped: List[SkippedRow] = field(default_factory=list)
    repitched: Set[int] = field(default_factory=set)

    def follow(self, note: SoundingNote) -> None:
        """Moves the note the channel holds through each transpose row reaching it.

        FamiTracker keeps the note a slide leaves, so each row's slide is measured from the note the
        channel holds once the slides before it applied, and a row the module leaves without its
        slide leaves the note where it was for the rows after it.
        """
        target = self.targets[(note.voice_id, self.channel_name)]
        held = target.cell_pitch(note.step, self.channel_name)
        for repitch in note.repitches:
            needed = target.cell_pitch(repitch.step, self.channel_name) - held
            applied = self._decide(repitch, needed)
            if applied != needed:
                self._report(note, repitch)

            if applied != NO_SLIDE:
                self.repitched.add(target.slot.index)

            held += applied

    def _decide(self, repitch: Repitch, needed: int) -> int:
        """The slide the row's cell carries, decided by the first frame that reaches it with a note."""
        cell = (repitch.place.pattern_index, repitch.place.row_index)
        if cell not in self.decided:
            self.decided[cell] = needed if abs(needed) <= MAX_SLIDE_SEMITONES else NO_SLIDE

        return self.decided[cell]

    def _report(self, note: SoundingNote, repitch: Repitch) -> None:
        self.skipped.append(
            SkippedRow(
                voice_id=note.voice_id,
                channel=self.channel_name,
                order_position=repitch.place.order_position,
                row_index=repitch.place.row_index,
                reason=SkipReason.UNREACHED_TRANSPOSE,
            )
        )

    @property
    def slides(self) -> Dict[PatternCell, int]:
        """The cells that move the note, by pattern index and row."""
        return {cell: semitones for cell, semitones in self.decided.items() if semitones != NO_SLIDE}


@dataclass(frozen=True)
class SlidePlan:
    """The note slides a module's transpose rows write, the rows it leaves without one, and the instruments they reach.

    FamiTracker's ``Qxy`` and ``Rxy`` move the channel's note by up to fifteen semitones at once and glide
    the period toward it. While an instrument's arpeggio in absolute mode runs, it reloads the period
    from the note every tick, which makes the move instant and exact. A transpose row therefore writes
    the slide from the note the channel holds to the note a note-on at the row's transpose would write,
    at the highest speed, and every instrument a slide reaches keeps its arpeggio running — see
    :func:`features_to_instrument_sequences`. On noise the note is the period, and both notes lie within
    the sixteen periods, so every noise slide is within reach.

    Attributes:
        slides: Per channel, the semitones each pattern cell moves the note by, keyed by pattern index
            and row.
        skipped_rows: The transpose rows the module plays without their slide, once for every frame
            that plays one so.
        repitched: The instruments a slide reaches.
    """

    slides: Dict[ChannelName, Dict[PatternCell, int]]
    skipped_rows: Tuple[SkippedRow, ...]
    repitched: FrozenSet[int]

    @classmethod
    def build(cls, walks: Mapping[ChannelName, PitchWalk], targets: RowTargets) -> SlidePlan:
        """Plans every transpose row of the song, following the notes the order sounds.

        A row moving the note further than a slide reaches, or a cell of a pattern several frames play
        needing another slide than the frame that decided it, is written without it and reported.

        Args:
            walks: Each channel's pass through the song, as playback makes it.
            targets: What a row naming a voice on a channel triggers.

        Returns:
            SlidePlan: The slides, the rows left without one, and the instruments the slides reach.
        """
        slides: Dict[ChannelName, Dict[PatternCell, int]] = {}
        skipped: List[SkippedRow] = []
        repitched: Set[int] = set()
        for channel_name in ChannelName.items():
            channel = _ChannelSlides(channel_name=channel_name, targets=targets)
            for note in walks[channel_name].notes:
                channel.follow(note)

            slides[channel_name] = channel.slides
            skipped.extend(channel.skipped)
            repitched |= channel.repitched

        return cls(
            slides=slides,
            skipped_rows=tuple(skipped),
            repitched=frozenset(repitched),
        )
