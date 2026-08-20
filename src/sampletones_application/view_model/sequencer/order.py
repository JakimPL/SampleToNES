from typing import Dict, Optional, Tuple

from pydantic import BaseModel

from sampletones_application.view_model.sequencer.aggregate import aggregate_labels
from sampletones_core.constants.enums import ChannelName
from sampletones_core.utils.display import display_id


class OrderEntryViewModel(BaseModel, frozen=True):
    position: int
    pattern_index: Optional[int]

    @property
    def label(self) -> str:
        return display_id(self.pattern_index)


class SequencerOrderViewModel(BaseModel, frozen=True):
    """The pattern sequence for one channel."""

    channel: ChannelName
    entries: Tuple[OrderEntryViewModel, ...]


class SequencerOrderTrackerViewModel(BaseModel, frozen=True):
    """The whole arrangement: order positions (columns) across channels (rows).

    The master row summarises each position across channels — the horizontal analog
    of the tracker's sample column — showing the shared pattern index or ``?`` when
    the channels disagree.
    """

    position_count: int
    channels: Dict[ChannelName, SequencerOrderViewModel]

    def entry_label(self, channel: ChannelName, position: int) -> str:
        entries = self.channels[channel].entries
        if position < len(entries):
            return entries[position].label

        return display_id(None)

    def master_label(self, position: int) -> str:
        values = {self.entry_label(channel, position) for channel in self.channels}
        return aggregate_labels(values, default=display_id(None))
