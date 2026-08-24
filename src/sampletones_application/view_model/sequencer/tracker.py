from typing import Callable, Dict, FrozenSet, Optional, Set, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import (
    display_id,
    display_transpose,
    display_volume,
)
from sampletones_shared.utils.agreement import Agreement


class SequencerCellViewModel(BaseModel, frozen=True):
    """One channel cell on one tracker row, pre-formatted for display.

    The columns are produced by :mod:`sampletones_core.utils.display`, the single
    source of tracker cell formatting (voice position, transpose, volume). The
    tracker grid renders :attr:`label`, the combined cell text.
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

    @property
    def label(self) -> str:
        return f"{self.voice} {self.transpose} {self.volume}"


def _sample_reading(cell: SequencerCellViewModel) -> str:
    """A cell's voice reading as the sample column speaks it.

    The column places a recording over the channels it covers, so it reads a sample by its number
    and a cut as a cut. A hand-written instrument is placed in the channel column that names it, so
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
    naming only hand-written instruments spans none, since each of those sounds on the one
    channel it is named in.
    """

    @property
    def subcolumn_channels(self) -> FrozenSet[ChannelName]:
        """Channels every sample column summary spans.

        A sample governs the channels its reconstruction covers, so its subcolumns
        summarize exactly those. Transpose and volume stand on their own, so a row
        naming no sample spans every channel.
        """
        return self.sample_channels or frozenset(self.cells)

    @property
    def sample(self) -> str:
        return self._aggregate(_sample_reading, display_id(None))

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
        return self._aggregate(lambda cell: cell.transpose, display_transpose(None))

    @property
    def volume(self) -> str:
        return self._aggregate(lambda cell: cell.volume, display_volume(None))

    def _aggregate(
        self,
        select: Callable[[SequencerCellViewModel], str],
        default: str,
    ) -> str:
        """Summarize one subcolumn across the channels the sample column spans.

        The summary holds a value only where every channel agrees on it, so
        :data:`MIXED` marks each way they can differ: a sample missing from one of
        its channels, a transpose set on some of them, or a row cut on some and
        blank on the rest. A row with no cells at all shows the empty default.
        """
        values: Set[str] = {select(self.cells[channel]) for channel in self.subcolumn_channels}
        return aggregate_labels(values, default=default)


class SequencerTrackerViewModel(BaseModel, frozen=True):
    """The tracker view for a single order frame across the four channels.

    Each channel plays its ``order[frame_index]`` pattern; the grid shows those
    patterns aligned row by row. Channels whose order is shorter than
    ``frame_index`` contribute empty cells.
    """

    frame_index: int
    frame_count: int
    rows: Tuple[SequencerRowViewModel, ...]
