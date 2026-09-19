import pytest

from sampletones_core.constants.general import MAX_PITCH, MAX_TIMER, MIN_PITCH, MIN_TIMER
from sampletones_player.registers.dividers import bent_dividers
from tests.suite.player import PLAYER_REFERENCE_PITCH, PLAYER_TIMER_TABLE


class TestBentDividers:
    """Each frame's divider is its note's own, moved by the steps the frame is bent by."""

    def test_an_unbent_frame_sounds_its_note_s_own_divider(self) -> None:
        assert bent_dividers((PLAYER_REFERENCE_PITCH,), (0,), PLAYER_TIMER_TABLE) == (
            PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH],
        )

    def test_every_frame_moves_by_its_own_bend(self) -> None:
        offsets = (3, -3, 40)
        dividers = bent_dividers((PLAYER_REFERENCE_PITCH,) * len(offsets), offsets, PLAYER_TIMER_TABLE)
        assert dividers == tuple(PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH] + offset for offset in offsets)

    def test_a_bend_past_the_register_stops_at_its_edge(self) -> None:
        dividers = bent_dividers((MIN_PITCH, MAX_PITCH), (MAX_TIMER, -MAX_TIMER), PLAYER_TIMER_TABLE)
        assert dividers == (MAX_TIMER, MIN_TIMER)

    def test_notes_and_bends_covering_different_frames_are_refused(self) -> None:
        with pytest.raises(ValueError):
            bent_dividers((PLAYER_REFERENCE_PITCH,), (0, 0), PLAYER_TIMER_TABLE)
