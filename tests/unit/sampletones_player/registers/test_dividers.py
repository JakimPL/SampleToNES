import pytest

from sampletones_core.constants.general import (
    MAX_PITCH,
    MAX_TIMER,
    MIN_PITCH,
    MIN_TIMER,
)
from sampletones_core.timers.nearest import nearest_pitch
from sampletones_player.registers.dividers import (
    anchored_pitches,
    bent_dividers,
)
from sampletones_player.specification.binary import SIGNED_BYTE_LIMIT
from tests.suite.player import PLAYER_REFERENCE_PITCH, PLAYER_TIMER_TABLE


class TestBentDividers:
    """Each frame's divider is its note's own, moved by the steps the frame is bent by."""

    def test_an_unbent_frame_sounds_its_note_s_own_divider(self) -> None:
        assert bent_dividers((PLAYER_REFERENCE_PITCH,), (0,), PLAYER_TIMER_TABLE) == (
            PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH],
        )

    def test_every_frame_moves_by_its_own_bend(self) -> None:
        offsets = (3, -3, 40)
        dividers = bent_dividers(
            (PLAYER_REFERENCE_PITCH,) * len(offsets),
            offsets,
            PLAYER_TIMER_TABLE,
        )
        assert dividers == tuple(PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH] + offset for offset in offsets)

    def test_a_bend_past_the_register_stops_at_its_edge(self) -> None:
        dividers = bent_dividers((MIN_PITCH, MAX_PITCH), (MAX_TIMER, -MAX_TIMER), PLAYER_TIMER_TABLE)
        assert dividers == (MAX_TIMER, MIN_TIMER)

    def test_notes_and_bends_covering_different_frames_are_refused(
        self,
    ) -> None:
        with pytest.raises(ValueError):
            bent_dividers((PLAYER_REFERENCE_PITCH,), (0, 0), PLAYER_TIMER_TABLE)


class TestAnchoredPitches:
    """A divider is counted from the frame's own note wherever the bend fits the plane's byte."""

    def test_a_bend_past_halfway_is_counted_from_the_frames_own_note(
        self,
    ) -> None:
        divider = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH] - SIGNED_BYTE_LIMIT + 1
        assert nearest_pitch(PLAYER_TIMER_TABLE, divider).pitch != PLAYER_REFERENCE_PITCH
        assert anchored_pitches((PLAYER_REFERENCE_PITCH,), (divider,), PLAYER_TIMER_TABLE) == (PLAYER_REFERENCE_PITCH,)

    def test_a_bend_past_the_byte_is_counted_from_the_nearest_pitch(
        self,
    ) -> None:
        divider = PLAYER_TIMER_TABLE[PLAYER_REFERENCE_PITCH] - SIGNED_BYTE_LIMIT - 1
        assert anchored_pitches((PLAYER_REFERENCE_PITCH,), (divider,), PLAYER_TIMER_TABLE) == (
            nearest_pitch(PLAYER_TIMER_TABLE, divider).pitch,
        )

    def test_notes_and_dividers_covering_different_frames_are_refused(
        self,
    ) -> None:
        with pytest.raises(ValueError):
            anchored_pitches((PLAYER_REFERENCE_PITCH,), (), PLAYER_TIMER_TABLE)
