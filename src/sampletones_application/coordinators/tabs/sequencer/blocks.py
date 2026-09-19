from functools import partial
from typing import Callable, Optional, ParamSpec

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
from sampletones_application.utils.gui.clipboard.protocol import TextClipboard
from sampletones_application.view_model.sequencer.region import (
    OrderCell,
    OrderRegion,
    TrackerCell,
    TrackerRegion,
)
from sampletones_shared.types.callback import VoidCallback

GestureParams = ParamSpec("GestureParams")


class SequencerBlocks:
    """The blocks both grids copy, cut and paste, and the two clipboards they travel on.

    A copy lands in this tab's own slot and, as text, on the system clipboard, so the same block
    reaches a paste here and a paste in another instance. A paste asks the system clipboard first
    and takes its text while that text is a block, which is what lets one instance hand a block to
    the next. The clipboard answers in its own time, so the blocks keep its last answer, and every
    question about the block in hand reads that answer.

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
        self._clipboard_text: str = ""
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

    def read_clipboard(self, then: VoidCallback) -> None:
        """Asks the system clipboard for its text, running ``then`` once the answer has landed.

        The answer is what the pastes and the menus offering them read from then on, so a gesture
        that asked first acts on the text standing on the clipboard as it answered.
        """
        self._text_clipboard.read(partial(self._take_clipboard_text, then))

    def after_reading_clipboard(
        self,
        paste: Callable[GestureParams, None],
    ) -> Callable[GestureParams, None]:
        """Holds a paste back until the system clipboard has answered, so it writes the block in hand then."""

        def wrapped(*args: GestureParams.args, **kwargs: GestureParams.kwargs) -> None:
            self.read_clipboard(partial(paste, *args, **kwargs))

        return wrapped

    def tracker_in_hand(self) -> Optional[TrackerBlock]:
        """The block a tracker paste would write: the system clipboard's while its text is one.

        Text another instance copied reads as a block here, so it stands ahead of the slot the
        tracker copied into, and text from anywhere else leaves that slot's own block in hand.
        """
        parsed = self._tracker_cache.block(self._clipboard_text)
        if parsed is not None:
            return parsed

        return self._clipboard.tracker_block

    def order_in_hand(self) -> Optional[OrderBlock]:
        """The block an order paste would write: the system clipboard's while its text is one.

        Text another instance copied reads as a block here, so it stands ahead of the slot the
        order copied into, and text from anywhere else leaves that slot's own block in hand.
        """
        parsed = self._order_cache.block(self._clipboard_text)
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

    def _take_clipboard_text(self, then: VoidCallback, text: str) -> None:
        self._clipboard_text = text
        then()
