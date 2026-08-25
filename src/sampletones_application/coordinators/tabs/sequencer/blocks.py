from typing import Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.clipboard import (
    OrderBlockText,
    ParsedBlockCache,
    ProjectSampleDirectory,
    SequencerClipboard,
    TrackerBlockText,
)
from sampletones_application.logic.sequencer.order import (
    OrderBlock,
    OrderBlockReader,
    OrderBlockWriter,
    SequencerOrderLogic,
)
from sampletones_application.logic.sequencer.tracker import (
    SequencerTrackerLogic,
    TrackerBlock,
    TrackerBlockReader,
    TrackerBlockWriter,
)
from sampletones_application.utils.gui.clipboard import TextClipboard
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)


class SequencerBlocks:
    """The blocks both grids copy, cut and paste, and the two clipboards they travel on.

    A copy lands in this tab's own slot and, as text, on the system clipboard, so the same block
    reaches a paste here and a paste in another instance. A paste reads the system clipboard first
    while what stands there is a block, which is what lets one instance hand a block to the next.

    Every gesture here reads and writes the project as it stands; recording what a gesture undoes
    is the caller's, so the coordinator wraps the writing ones in a history transaction.
    """

    def __init__(
        self,
        tracker_logic: SequencerTrackerLogic,
        order_logic: SequencerOrderLogic,
        project_controller: ProjectController,
        *,
        text_clipboard: TextClipboard,
    ) -> None:
        self._clipboard: SequencerClipboard = SequencerClipboard()
        self._text_clipboard: TextClipboard = text_clipboard
        self._tracker_text: TrackerBlockText = TrackerBlockText(
            samples=ProjectSampleDirectory(project_controller),
        )
        self._order_text: OrderBlockText = OrderBlockText()
        self._tracker_cache: ParsedBlockCache[TrackerBlock] = ParsedBlockCache(self._tracker_text.parse)
        self._order_cache: ParsedBlockCache[OrderBlock] = ParsedBlockCache(self._order_text.parse)
        self._tracker_reader: TrackerBlockReader = TrackerBlockReader(tracker_logic)
        self._tracker_writer: TrackerBlockWriter = TrackerBlockWriter(tracker_logic)
        self._order_reader: OrderBlockReader = OrderBlockReader(order_logic)
        self._order_writer: OrderBlockWriter = OrderBlockWriter(order_logic)

    def can_paste_tracker(self) -> bool:
        """Whether the tracker has a block to write, which is what its Paste item is offered on."""
        return self.tracker_in_hand() is not None

    def can_paste_order(self) -> bool:
        """Whether the order has a block to write, which is what its Paste item is offered on."""
        return self.order_in_hand() is not None

    def tracker_in_hand(self) -> Optional[TrackerBlock]:
        """The block a tracker paste would write: the system clipboard's while its text is one.

        Text another instance copied reads as a block here, so it stands ahead of the slot the
        tracker copied into, and text from anywhere else leaves that slot's own block in hand.
        """
        parsed = self._tracker_cache.block(self._text_clipboard.read())
        if parsed is not None:
            return parsed

        return self._clipboard.tracker_block

    def order_in_hand(self) -> Optional[OrderBlock]:
        """The block an order paste would write: the system clipboard's while its text is one.

        Text another instance copied reads as a block here, so it stands ahead of the slot the
        order copied into, and text from anywhere else leaves that slot's own block in hand.
        """
        parsed = self._order_cache.block(self._text_clipboard.read())
        if parsed is not None:
            return parsed

        return self._clipboard.order_block

    def copy_tracker(self, region: TrackerRegion) -> None:
        """Puts the tracker's selected block on both clipboards, for a paste to replay.

        The slot keeps the block exactly, and the system clipboard keeps the text form of it, so
        the same copy reaches a paste here and a paste in another instance.
        """
        block = self._tracker_reader.read(region)
        self._clipboard.store_tracker_block(block)
        self._text_clipboard.write(self._tracker_text.state(block, region))

    def cut_tracker(self, region: TrackerRegion) -> None:
        """Takes the block a region covers onto the clipboard, then empties what it covered."""
        self.copy_tracker(region)
        self._tracker_writer.clear(region)

    def clear_tracker(self, region: TrackerRegion) -> None:
        """Empties every cell a tracker region covers, leaving the clipboards as they stand."""
        self._tracker_writer.clear(region)

    def paste_tracker(self, cell: TrackerCell) -> None:
        """Writes the block the tracker has in hand at a cell, while a copy has been made."""
        block = self.tracker_in_hand()
        if block is not None:
            self._tracker_writer.write(block, cell)

    def copy_order(self, region: OrderRegion) -> None:
        """Puts the order's selected block on both clipboards, for a paste to replay.

        The slot keeps the block exactly, and the system clipboard keeps the text form of it, so
        the same copy reaches a paste here and a paste in another instance.
        """
        block = self._order_reader.read(region)
        self._clipboard.store_order_block(block)
        self._text_clipboard.write(self._order_text.state(block, region))

    def cut_order(self, region: OrderRegion) -> None:
        """Takes the block a region covers onto the clipboard, then silences what it covered."""
        self.copy_order(region)
        self._order_writer.clear(region)

    def clear_order(self, region: OrderRegion) -> None:
        """Silences every cell an order region covers, leaving the clipboards as they stand."""
        self._order_writer.clear(region)

    def paste_order(self, cell: OrderCell) -> None:
        """Writes the block the order has in hand at a cell, while a copy has been made."""
        block = self.order_in_hand()
        if block is not None:
            self._order_writer.write(block, cell)
