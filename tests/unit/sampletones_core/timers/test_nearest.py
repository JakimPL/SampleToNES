from typing import Dict, Final, Tuple

import pytest

from sampletones_core.constants.general import MAX_TIMER
from sampletones_core.timers.nearest import NearestPitch, nearest_pitch, nearest_pitches
from sampletones_core.timers.utils import get_timer_table
from sampletones_shared.music import Tuning

LOW_PITCH: Final[int] = 40
HIGH_PITCH: Final[int] = 41
SHARING_PITCH: Final[int] = 42
LOW_TIMER: Final[int] = 100
HIGH_TIMER: Final[int] = 90
HALFWAY: Final[int] = (LOW_TIMER + HIGH_TIMER) // 2


@pytest.fixture(scope="module")
def table() -> Dict[int, int]:
    return get_timer_table(Tuning())


@pytest.fixture(scope="module")
def nearest(table: Dict[int, int]) -> Tuple[NearestPitch, ...]:
    return nearest_pitches(table)


class TestNamingADividerByItsNearestPitch:
    def test_every_divider_the_register_holds_is_named(self, nearest: Tuple[NearestPitch, ...]) -> None:
        assert len(nearest) == MAX_TIMER + 1

    def test_a_pitch_s_own_divider_names_the_lowest_pitch_sounding_it(
        self,
        table: Dict[int, int],
        nearest: Tuple[NearestPitch, ...],
    ) -> None:
        for timer in table.values():
            named = nearest[timer]
            assert named.offset == 0
            assert named.pitch == min(other for other, sounded in table.items() if sounded == timer)

    def test_no_pitch_lies_nearer_than_the_one_named(
        self,
        table: Dict[int, int],
        nearest: Tuple[NearestPitch, ...],
    ) -> None:
        for divider, named in enumerate(nearest):
            assert table[named.pitch] + named.offset == divider
            assert all(abs(named.offset) <= abs(divider - timer) for timer in table.values())


class TestADividerBetweenTwoPitches:
    """A hand-built table, so the halfway point and a shared divider are known exactly."""

    @pytest.fixture
    def nearest(self) -> Tuple[NearestPitch, ...]:
        return nearest_pitches({LOW_PITCH: LOW_TIMER, HIGH_PITCH: HIGH_TIMER, SHARING_PITCH: HIGH_TIMER})

    def test_a_shared_divider_names_the_lower_of_its_pitches(self, nearest: Tuple[NearestPitch, ...]) -> None:
        assert nearest[HIGH_TIMER] == NearestPitch(pitch=HIGH_PITCH, offset=0)

    def test_the_halfway_divider_goes_to_the_higher_pitch(self, nearest: Tuple[NearestPitch, ...]) -> None:
        assert nearest[HALFWAY] == NearestPitch(pitch=HIGH_PITCH, offset=HALFWAY - HIGH_TIMER)

    def test_a_divider_past_halfway_goes_to_the_lower_pitch(self, nearest: Tuple[NearestPitch, ...]) -> None:
        assert nearest[HALFWAY + 1] == NearestPitch(pitch=LOW_PITCH, offset=HALFWAY + 1 - LOW_TIMER)

    def test_dividers_beyond_the_table_take_the_pitch_at_its_edge(self, nearest: Tuple[NearestPitch, ...]) -> None:
        assert nearest[0].pitch == HIGH_PITCH
        assert nearest[MAX_TIMER].pitch == LOW_PITCH

    def test_an_empty_table_is_refused(self) -> None:
        with pytest.raises(ValueError):
            nearest_pitches({})


class TestNamingOneDivider:
    def test_one_divider_is_named_as_the_whole_table_names_it(
        self,
        table: Dict[int, int],
        nearest: Tuple[NearestPitch, ...],
    ) -> None:
        for divider in (0, HALFWAY, table[max(table)], MAX_TIMER):
            assert nearest_pitch(table, divider) == nearest[divider]
