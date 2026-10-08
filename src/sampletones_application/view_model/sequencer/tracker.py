from typing import Callable, Dict, Final, FrozenSet, Optional, Set, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.pitch import RowPitch
from sampletones_core.project.patterns.row import NoteCommand
from sampletones_core.utils.display import (
    display_id,
    display_pitch,
    display_volume,
)
from sampletones_shared.utils.agreement import Agreement

NO_REACH: Final[int] = 0


class SequencerCellViewModel(BaseModel, frozen=True):
    """One channel cell on one tracker row, pre-formatted for display.

    The columns are produced by :mod:`sampletones_core.utils.display`, the single
    source of tracker cell formatting (voice position, pitch, volume). The
    tracker grid renders :attr:`label`, the combined cell text. The values the
    faces were printed from travel beside them, so a reader describing the cell
    speaks of what it holds.
    """

    voice: str
    transpose: str
    volume: str
    kind: Optional[VoiceKind]
    """The kind of the voice this cell names, absent where it names none.

    The cell reads its voice by list position, which says nothing about what that voice is. The
    kind travels beside it so a reader of the cell — the sample column's summary, the color the
    slot takes — knows which of the two it is looking at.
    """
    pitch: Optional[RowPitch]
    level: Optional[int]
    command: Optional[NoteCommand]

    @property
    def label(self) -> str:
        return f"{self.voice} {self.transpose} {self.volume}"


def _sample_reading(cell: SequencerCellViewModel) -> str:
    """A cell's voice reading as the sample column speaks it.

    The column places a recording over the channels it covers, so it reads a sample by its number
    and a cut as a cut. An instrument is placed in the channel column that names it, so
    it reads as empty here and leaves the summary to the channels the column governs.
    """
    if cell.kind is VoiceKind.INSTRUMENT:
        return display_id(None)

    return cell.voice


class SequencerRowViewModel(BaseModel, frozen=True):
    index: int
    cells: Dict[ChannelName, SequencerCellViewModel]
    sample_channels: FrozenSet[ChannelName]
    """Channels the row's samples span — the union of their reconstructions' channels.

    A sample governs the channels its reconstruction covers, so the sample column reads its
    reference across exactly those and a sample missing from one of them reads as mixed. A row
    naming only instruments spans none, since each of those sounds on the one
    channel it is named in.
    """
    carried_channels: FrozenSet[ChannelName]
    """Channels a sample is playing on at this row, whichever row of the frame started it.

    The reading runs down the frame from its first row, so a channel cut since, or now carrying an
    instrument, falls out of it. A row naming no sample hands its pitch and volume to these.
    """

    @property
    def note_channels(self) -> FrozenSet[ChannelName]:
        """Channels the sample column's voice slot summarizes.

        A sample governs the channels its reconstruction covers, so the slot summarizes exactly
        those. A row naming no sample spans every channel, so a row cut on each reads as a cut.
        """
        return self.sample_channels or frozenset(self.cells)

    @property
    def offset_channels(self) -> FrozenSet[ChannelName]:
        """Channels the sample column's pitch and volume summarize, and write to.

        A row placing a sample spans that sample's channels, and a row below it the channels a
        sample is still playing on. A row where no sample plays spans none and reads empty.
        """
        return self.sample_channels or self.carried_channels

    @property
    def takes_offsets(self) -> bool:
        """Whether a pitch or a volume typed in the sample column reaches a channel of this row."""
        return bool(self.offset_channels)

    @property
    def sample(self) -> str:
        return self._aggregate(
            _sample_reading,
            display_id(None),
            self.note_channels,
        )

    @property
    def sample_kind(self) -> Optional[VoiceKind]:
        """The kind of voice the sample column's slot names, absent where its channels disagree.

        The slot speaks for the channels the row's samples cover, so it states a kind where every
        one of those channels names a voice of that kind. A row naming no sample covers none and
        states none, which is what an empty slot and a cut row are.
        """
        kinds = Agreement.collapse(self.cells[channel].kind for channel in self.sample_channels)
        return kinds.resolve(absent=None, mixed=None)

    @property
    def transpose(self) -> str:
        return self._aggregate(
            lambda cell: cell.transpose,
            display_pitch(None),
            self.offset_channels,
        )

    @property
    def volume(self) -> str:
        return self._aggregate(
            lambda cell: cell.volume,
            display_volume(None),
            self.offset_channels,
        )

    def _aggregate(
        self,
        select: Callable[[SequencerCellViewModel], str],
        default: str,
        channels: FrozenSet[ChannelName],
    ) -> str:
        """Summarize one subcolumn across the channels the sample column spans in it.

        The summary holds a value only where every channel agrees on it, so
        :data:`MIXED` marks each way they can differ: a sample missing from one of
        its channels, a transpose set on some of them, or a row cut on some and
        blank on the rest. A subcolumn spanning no channel shows the empty default.
        """
        values: Set[str] = {select(self.cells[channel]) for channel in channels}
        return aggregate_labels(values, default=default)


class SequencerContextRowViewModel(BaseModel, frozen=True):
    """A row of another frame, drawn beside the shown one so the song reads on past the frame's edges.

    ``row`` reads as it does while its own frame is shown, and ``frame_index`` names that frame.
    """

    frame_index: int
    row: SequencerRowViewModel


class SequencerTrackerViewModel(BaseModel, frozen=True):
    """The tracker view for a single order frame across the four channels, with the song around it.

    Each channel plays its ``order[frame_index]`` pattern; the grid shows those
    patterns aligned row by row. Channels whose order is shorter than
    ``frame_index`` contribute empty cells.

    ``lead`` holds the rows the song plays before the frame and ``trail`` the rows it plays after,
    each in playing order and as many as the tracker reaches, so a row near the frame's edge stands
    among its neighbors. Both end where the song does.
    """

    frame_index: int
    frame_count: int
    rows: Tuple[SequencerRowViewModel, ...]
    lead: Tuple[SequencerContextRowViewModel, ...]
    trail: Tuple[SequencerContextRowViewModel, ...]
