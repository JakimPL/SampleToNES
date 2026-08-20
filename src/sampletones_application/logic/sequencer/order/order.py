from typing import Callable, Optional

from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.view_model.sequencer.order import (
    OrderEntryViewModel,
    SequencerOrderTrackerViewModel,
    SequencerOrderViewModel,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.song import Song
from sampletones_shared.utils.callbacks import CallbackMixin


class SequencerOrderLogic(CallbackMixin):
    """Builds the order arrangement view model and exposes order mutations.

    Navigation (the current frame) is owned by :class:`SequencerTrackerLogic`; this
    class is only responsible for which pattern index each channel plays at every
    order position, and how to change that arrangement.
    """

    def __init__(self, project_controller: ProjectController) -> None:
        self._controller = project_controller

        self.on_order_changed: Optional[Callable[[SequencerOrderTrackerViewModel], None]] = None

    def build_order(self) -> SequencerOrderTrackerViewModel:
        song = self._controller.project.song
        channels = {channel: self._build_channel_view(channel, song) for channel in ChannelName.items()}
        return SequencerOrderTrackerViewModel(
            position_count=song.order_length(),
            channels=channels,
        )

    def push_order(self) -> None:
        self.call(self.on_order_changed, self.build_order())

    def refresh(self) -> None:
        self.push_order()

    def set_order_entry(
        self,
        channel: ChannelName,
        position: int,
        pattern_index: Optional[int],
    ) -> None:
        self._controller.set_order_entry(channel, position, pattern_index)

    def set_master_entry(self, position: int, pattern_index: Optional[int]) -> None:
        for channel in ChannelName.items():
            self._controller.set_order_entry(channel, position, pattern_index)

    def write_entry(
        self,
        channel: Optional[ChannelName],
        position: int,
        pattern_index: Optional[int],
    ) -> None:
        """Plays a pattern index at a position, the master row settling every channel at once.

        This is the rule the table's two kinds of row follow, kept in one place so a gesture
        reaching across them writes what the reader typing into each by hand would.
        """
        if channel is None:
            self.set_master_entry(position, pattern_index)
        else:
            self.set_order_entry(channel, position, pattern_index)

    def entry(self, channel: ChannelName, position: int) -> Optional[int]:
        """The pattern index a channel plays at a position, empty past the order's last frame."""
        order = self._controller.song.order
        if position >= len(order):
            return None

        return order[position].get(channel)

    def position_count(self) -> int:
        return self._controller.order_length

    def append_frame(self) -> None:
        """Adds one empty frame (all channels silent) after the order's last."""
        self._controller.append_frame()

    def remove_from_order(self, position: int) -> None:
        self._controller.remove_frame(position)

    def insert_frame(self, position: int) -> None:
        """Inserts one empty frame (all channels silent) at ``position``."""
        self._controller.insert_frame(position)

    def duplicate_frame(self, position: int) -> None:
        """Repeats the frame at ``position`` directly after it, playing the same patterns."""
        self._controller.duplicate_frame(position)

    def clone_frame(self, position: int) -> None:
        """Inserts a copy of the frame at ``position`` directly after it, with its own patterns."""
        self._controller.clone_frame(position)

    def clear_frame(self, position: int) -> None:
        """Empties every channel in the frame at ``position``."""
        self._controller.clear_frame(position)

    def move_frame(self, from_position: int, to_position: int) -> None:
        self._controller.move_frame(from_position, to_position)

    def _build_channel_view(
        self,
        channel: ChannelName,
        song: Song,
    ) -> SequencerOrderViewModel:
        entries = tuple(
            OrderEntryViewModel(
                position=position,
                pattern_index=frame.get(channel),
            )
            for position, frame in enumerate(song.order)
        )
        return SequencerOrderViewModel(
            channel=channel,
            entries=entries,
        )
