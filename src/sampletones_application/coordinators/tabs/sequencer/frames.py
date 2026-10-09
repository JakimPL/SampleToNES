from typing import Callable

from sampletones_application.coordinators.tabs.sequencer.playhead import SequencerPlayhead
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.sequencer.order import SequencerOrderLogic
from sampletones_application.logic.sequencer.playback.playhead import (
    remap_after_insert,
    remap_after_move,
    remap_after_remove,
)
from sampletones_application.logic.sequencer.playback.song_player import SongPlayerLogic
from sampletones_application.logic.sequencer.tracker import SequencerTrackerLogic


class SequencerFrames:
    """The gestures that reshape the order, each carrying the playhead over what it moved.

    Adding, removing and moving a frame shifts every frame after it, so a playhead standing on
    one of them follows it to where it went, and the grid moves to the frame the reader is now
    working on. A gesture that leaves the order's shape alone leaves the playhead alone too.
    """

    def __init__(
        self,
        order_logic: SequencerOrderLogic,
        tracker_logic: SequencerTrackerLogic,
        song_player_logic: SongPlayerLogic,
        project_controller: ProjectController,
        playhead: SequencerPlayhead,
    ) -> None:
        self._order_logic = order_logic
        self._tracker_logic = tracker_logic
        self._song_player_logic = song_player_logic
        self._project_controller = project_controller
        self._playhead = playhead

    def remove(self, position: int) -> None:
        """Takes a frame out of the order, carrying the playhead over the frames that close up."""
        length_before = self._project_controller.order_length
        self._order_logic.remove_from_order(position)
        self._relocate_playhead(
            lambda playhead: remap_after_remove(
                playhead,
                position,
                length_before - 1,
            )
        )

    def duplicate(self, position: int) -> None:
        """Puts a copy of a frame after it, sharing the patterns the original names."""
        self._order_logic.duplicate_frame(position)
        self._settle_inserted_frame(position + 1)

    def clone(self, position: int) -> None:
        """Puts a copy of a frame after it, over patterns of its own."""
        self._order_logic.clone_frame(position)
        self._settle_inserted_frame(position + 1)

    def insert(self, position: int) -> None:
        """Puts an empty frame after a frame, and moves to it."""
        self._order_logic.insert_frame(position + 1)
        self._relocate_playhead(
            lambda playhead: remap_after_insert(
                playhead,
                position + 1,
            )
        )
        self._select_frame_when_idle(position + 1)

    def clear(self, position: int) -> None:
        """Clears every channel in the frame; no index shift, so the playhead is left in place.

        A sounding voice keeps ringing across the now-empty frame (only an explicit note-off cuts it).
        """
        self._order_logic.clear_frame(position)

    def move(self, from_position: int, to_position: int) -> None:
        """Moves a frame to another place in the order, and shows it where it landed."""
        self._order_logic.move_frame(from_position, to_position)
        self._relocate_playhead(
            lambda playhead: remap_after_move(
                playhead,
                from_position,
                to_position,
            )
        )
        self._tracker_logic.select_frame(to_position)

    def play_from(self, position: int) -> None:
        """Plays from a frame: relocates the playhead when already playing, else starts there."""
        if self._song_player_logic.is_playing():
            self._song_player_logic.seek(position)
        else:
            self._song_player_logic.play_from(position)

    def select(self, frame_index: int) -> None:
        """Selects an order frame in the tracker, and moves the playhead too when following.

        While the view follows the playhead, choosing another order during playback relocates the
        playhead to it (the seek no-ops when stopped); otherwise the selection only changes which
        pattern is edited, leaving playback where it is.
        """
        self._tracker_logic.select_frame(frame_index)
        if self._song_player_logic.follow_mode.follows_pattern:
            self._song_player_logic.seek(frame_index)

    def _settle_inserted_frame(self, position: int) -> None:
        """Carries the playhead and the shown frame over a frame that has just been inserted.

        A frame arriving at ``position`` pushes every later frame one along, so a playhead
        standing on one of them follows it, and the grid moves to the new frame for the reader
        to work on.
        """
        self._relocate_playhead(
            lambda playhead: remap_after_insert(
                playhead,
                position,
            )
        )
        self._select_frame_when_idle(position)

    def _relocate_playhead(self, remap: Callable[[int], int]) -> None:
        """Keeps the live playhead on the frame it was sounding after a structural order edit.

        Both grids take the new position straight away, ahead of the worker's next row update, so
        rapid edits (e.g. a held Alt+arrow) stay in step, and a paused playhead — which reports no
        further rows — is marked on the frame the edit moved it to.
        """
        position = self._playhead.position
        if position is None:
            return

        order_position = remap(position.order_position)
        if order_position == position.order_position:
            return

        self._playhead.stand_at(order_position, position.row_index)
        self._song_player_logic.relocate(order_position)
        self._playhead.mark()

    def _select_frame_when_idle(self, frame_index: int) -> None:
        """Moves the editor selection to a frame, unless playback is actively driving it."""
        if not self._song_player_logic.is_playing():
            self._tracker_logic.select_frame(frame_index)
