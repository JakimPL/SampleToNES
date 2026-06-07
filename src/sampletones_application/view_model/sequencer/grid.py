from typing import Dict, Tuple

from pydantic import BaseModel

from sampletones_core.constants.enums import GeneratorName


class SequencerCellViewModel(BaseModel, frozen=True):
    """One channel cell on one tracker row, pre-formatted for display.

    The columns are produced by :mod:`sampletones_core.utils.display`, the single
    source of tracker cell formatting (sample position, transpose, volume). The
    grid renders :attr:`label`, the combined cell text.
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

    @property
    def sample_label(self) -> str:
        instruments = {cell.instrument for cell in self.cells.values()}
        if len(instruments) == 1:
            return next(iter(instruments))

        return "?"


class SequencerGridViewModel(BaseModel, frozen=True):
    """The tracker view for a single order frame across the four channels.

    Each channel plays its ``order[frame_index]`` pattern; the grid shows those
    patterns aligned row by row. Channels whose order is shorter than
    ``frame_index`` contribute empty cells.
    """

    frame_index: int
    frame_count: int
    rows: Tuple[SequencerRowViewModel, ...]
