from typing import Optional

from sampletones_application.logic.sequencer.order import OrderBlock
from sampletones_application.logic.sequencer.tracker import TrackerBlock


class SequencerClipboard:
    """Holds the block each sequencer grid last copied, one slot per grid.

    Separate slots are what keep a paste in the grid it belongs to: the tracker reads only what a
    tracker copied, so a block never has to be asked which grid it came from.

    A slot outlives the project it was filled from, because a project is replaced on every undo
    and redo as well as on opening a document, and a copy the reader made is theirs to keep across
    all of it. A note naming a sample the project in place lacks is settled where the block is
    written.
    """

    def __init__(self) -> None:
        self._tracker_block: Optional[TrackerBlock] = None
        self._order_block: Optional[OrderBlock] = None

    @property
    def tracker_block(self) -> Optional[TrackerBlock]:
        """The block the tracker last copied, present once a copy has been made."""
        return self._tracker_block

    def store_tracker_block(self, block: TrackerBlock) -> None:
        self._tracker_block = block

    @property
    def order_block(self) -> Optional[OrderBlock]:
        """The block the order last copied, present once a copy has been made."""
        return self._order_block

    def store_order_block(self, block: OrderBlock) -> None:
        self._order_block = block
