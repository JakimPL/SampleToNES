from typing import Callable, Dict, FrozenSet, Set, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_core.constants.enums import GeneratorName
from sampletones_core.utils.display import (
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
        """Channels every sample column summary spans.

        A sample governs the channels its reconstruction covers, so its subcolumns
        summarise exactly those. Transpose and volume exist independently of an
        instrument, so a row with no sample spans every channel.
        """
        return self.relevant_generators or frozenset(self.cells)

    @property
    def sample_instrument(self) -> str:
        return self._aggregate(lambda cell: cell.instrument, display_id(None))

    @property
    def sample_transpose(self) -> str:
        return self._aggregate(lambda cell: cell.transpose, display_transpose(None))

    @property
    def sample_volume(self) -> str:
        return self._aggregate(lambda cell: cell.volume, display_volume(None))

    def _aggregate(
        self,
        select: Callable[[SequencerCellViewModel], str],
        default: str,
    ) -> str:
        """Summarise one subcolumn across the channels the sample column spans.

        The summary holds a value only where every channel agrees on it, so
        :data:`MIXED` marks each way they can differ: a sample missing from one of
        its channels, a transpose set on some of them, or a row cut on some and
        blank on the rest. A row with no cells at all shows the empty default.
        """
        values: Set[str] = {select(self.cells[generator]) for generator in self.subcolumn_generators}
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
