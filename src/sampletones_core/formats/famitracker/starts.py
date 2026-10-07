from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.rows.levels import RowPlace
from sampletones_core.exporters.rows.transpose import NoteStart, PatternCell, PitchWalk
from sampletones_core.exporters.skipped import SkippedRow, SkipReason


@dataclass
class _ChannelStarts:
    """One channel's pass through the note-ons the order reaches, deciding each pattern cell once."""

    channel_name: ChannelName
    decided: Dict[PatternCell, Optional[int]] = field(default_factory=dict)
    skipped: List[SkippedRow] = field(default_factory=list)

    def read(self, place: RowPlace, start: NoteStart) -> None:
        """Takes what a note-on started in one frame, the first frame reaching its cell deciding it."""
        cell = (place.pattern_index, place.row_index)
        if cell not in self.decided:
            self.decided[cell] = start.step
            return

        if self.decided[cell] != start.step:
            self.skipped.append(
                SkippedRow(
                    voice_id=start.voice_id,
                    channel=self.channel_name,
                    order_position=place.order_position,
                    row_index=place.row_index,
                    reason=SkipReason.CARRIED_PITCH,
                )
            )


@dataclass(frozen=True)
class StartPlan:
    """The note every note-on cell of a module starts at, and the frames that reach a cell needing another.

    A module stores a pattern once for every frame that plays it, so a note-on cell writes one note. A
    row stating a pitch starts at it in every frame, and a sample stating none starts as recorded, so
    every frame agrees on those cells. An instrument stating no pitch starts on the pitch its channel
    is sounding, which the frames before decide, so a pattern the order plays after different pitches
    needs a different note in that cell per frame. The first frame reaching the cell decides its
    note, and every later frame needing another is reported.

    Attributes:
        starts: Per channel, the step each note-on cell starts at, keyed by pattern index and row,
            and ``None`` where the cell starts nothing.
        skipped_rows: The note-ons the module plays at another pitch than the song, once for every
            frame that plays one so.
    """

    starts: Dict[ChannelName, Dict[PatternCell, Optional[int]]]
    skipped_rows: Tuple[SkippedRow, ...]

    @classmethod
    def build(cls, walks: Mapping[ChannelName, PitchWalk]) -> StartPlan:
        """Decides every note-on cell of the song from the frames the order plays it in.

        Args:
            walks: Each channel's pass through the song, as playback makes it.

        Returns:
            StartPlan: The step each cell starts at, and the frames written at another.
        """
        starts: Dict[ChannelName, Dict[PatternCell, Optional[int]]] = {}
        skipped: List[SkippedRow] = []
        for channel_name in ChannelName.items():
            channel = _ChannelStarts(channel_name=channel_name)
            for place, start in walks[channel_name].starts.items():
                channel.read(place, start)

            starts[channel_name] = channel.decided
            skipped.extend(channel.skipped)

        return cls(starts=starts, skipped_rows=tuple(skipped))
