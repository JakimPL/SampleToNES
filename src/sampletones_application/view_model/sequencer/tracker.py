from typing import Callable, Dict, FrozenSet, Set, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import (
    NOTE_OFF,
    display_id,
    display_transpose,
    display_volume,
)


class SequencerCellViewModel(BaseModel, frozen=True):
    """One channel cell on one tracker row, pre-formatted for display.

    The columns are produced by :mod:`sampletones_core.utils.display`, the single
    source of tracker cell formatting (sample position, transpose, volume). The
    tracker grid renders :attr:`label`, the combined cell text.
    """

    instrument: str
    transpose: str
    volume: str

    @property
    def label(self) -> str:
        return f"{self.instrument} {self.transpose} {self.volume}"


class SequencerRowViewModel(BaseModel, frozen=True):
    index: int
    cells: Dict[GeneratorName, SequencerCellViewModel]
    relevant_generators: FrozenSet[GeneratorName]
    """Channels the row's sample(s) span — the union of their reconstructions' channels.

    The sample column summarises a subcolumn only across these channels, so a
    sample that spans more channels than it currently occupies reads as mixed.
    """

    @property
    def subcolumn_generators(self) -> FrozenSet[GeneratorName]:
        """Channels the sample column's transpose/volume span.

        Transpose and volume exist independently of an instrument, so on a row with
        no sample they fall back to every channel; otherwise they track the
        sample's channels exactly like the instrument does.
        """
        return self.relevant_generators or frozenset(self.cells)

    @property
    def sample_instrument(self) -> str:
        """The sample column's note value.

        A referenced sample wins: the column shows its position (or :data:`MIXED` when the sample
        spans more channels than it occupies here). With no sample present, the column reads ``--``
        only when every channel is a note-off; any other mix — including a half-cut row of some
        note-off and some blank — reads as empty.
        """
        if self.relevant_generators:
            return self._aggregate(self.relevant_generators, lambda cell: cell.instrument, display_id(None))

        if self.cells and all(cell.instrument == NOTE_OFF for cell in self.cells.values()):
            return NOTE_OFF

        return display_id(None)

    @property
    def sample_transpose(self) -> str:
        return self._aggregate(self.subcolumn_generators, lambda cell: cell.transpose, display_transpose(None))

    @property
    def sample_volume(self) -> str:
        return self._aggregate(self.subcolumn_generators, lambda cell: cell.volume, display_volume(None))

    def _aggregate(
        self,
        generators: FrozenSet[GeneratorName],
        select: Callable[[SequencerCellViewModel], str],
        default: str,
    ) -> str:
        """Summarise one subcolumn across the given channels.

        The summary holds a value only when every channel agrees on it, so a sample
        missing from one of its channels (an empty cell there) reads as
        :data:`MIXED`. With no channels the empty default is shown.
        """
        values: Set[str] = {select(self.cells[generator]) for generator in generators}
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
