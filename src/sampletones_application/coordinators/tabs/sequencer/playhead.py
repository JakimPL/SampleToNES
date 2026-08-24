from typing import Optional

from sampletones_application.ui.panels.sequencer.order.panel import GUISequencerOrderPanel
from sampletones_application.ui.panels.sequencer.tracker.panel import GUISequencerTrackerPanel
from sampletones_core.project.song_position import SongPosition


class SequencerPlayhead:
    """Where the song is sounding, and the marks both grids carry to show it.

    The order grid marks the frame the playhead sounds; the tracker takes the whole position,
    since the row it marks belongs to the pattern of that frame. Standing the playhead somewhere
    and marking it are separate steps, so a caller that also moves the shown frame can do that
    first and leave the marks landing on the pattern already in view.
    """

    def __init__(
        self,
        tracker_panel: GUISequencerTrackerPanel,
        order_panel: GUISequencerOrderPanel,
    ) -> None:
        self._tracker_panel = tracker_panel
        self._order_panel = order_panel
        self._position: Optional[SongPosition] = None

    @property
    def position(self) -> Optional[SongPosition]:
        """The position the song is sounding, absent while nothing is."""
        return self._position

    def stand_at(self, order_position: int, row_index: int) -> None:
        """Puts the playhead on a row of a frame, leaving the marks for :meth:`mark`."""
        self._position = SongPosition(
            order_position=order_position,
            row_index=row_index,
        )

    def stop(self) -> None:
        """Takes the playhead off the song, clearing the marks it carried."""
        self._position = None
        self.mark()

    def mark(self) -> None:
        """Puts the playhead's marks where it stands, on both grids."""
        position = self._position
        self._tracker_panel.set_playing_position(position)
        self._order_panel.set_playing_position(
            position.order_position if position is not None else None,
        )
