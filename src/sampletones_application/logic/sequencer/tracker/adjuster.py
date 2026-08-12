from typing import Iterator, List, Optional, Tuple

from sampletones_application.view_model.sequencer.region import TrackerRegion
from sampletones_core.constants.enums import GeneratorName

from .tracker import SequencerTrackerLogic


class TrackerRegionAdjuster:
    """Shifts transpose and volume across the cells a region covers.

    A region names its edges as subcolumns while these two gestures act on whole cells, so an
    adjustment reads the columns behind the region and reaches each of their channels once. The
    sample column stands for the channels a value typed in it writes to, which is what keeps a
    region covering it and a channel beneath it moving that channel a single step.

    Each cell reaches the grid through the single-cell adjustment that already governs it, so a
    shift over a region lands exactly the writes the same nudge repeated by hand would make.
    """

    def __init__(self, tracker_logic: SequencerTrackerLogic) -> None:
        self._tracker = tracker_logic

    def adjust_transpose(self, region: TrackerRegion, delta: int) -> None:
        """Shifts every covered cell's transpose by ``delta`` semitones."""
        for row_index, generator in self._cells(region):
            self._tracker.adjust_transpose(generator, row_index, delta)

    def adjust_volume(self, region: TrackerRegion, delta: int) -> None:
        """Shifts every covered cell's volume by ``delta``."""
        for row_index, generator in self._cells(region):
            self._tracker.adjust_volume(generator, row_index, delta)

    def _cells(
        self,
        region: TrackerRegion,
    ) -> Iterator[Tuple[int, GeneratorName]]:
        """The channel cells a region reaches, row by row and each named once."""
        columns = region.columns
        for row_index in region.rows:
            for generator in self._channels(columns, row_index):
                yield row_index, generator

    def _channels(
        self,
        columns: Tuple[Optional[GeneratorName], ...],
        row_index: int,
    ) -> List[GeneratorName]:
        """The channels a row's columns reach, the sample column standing for the ones it governs."""
        channels: List[GeneratorName] = []
        for column in columns:
            if column is None:
                channels.extend(self._tracker.relevant_generators(row_index))
            else:
                channels.append(column)

        return list(dict.fromkeys(channels))
