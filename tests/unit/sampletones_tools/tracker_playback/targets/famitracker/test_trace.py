from typing import Final, List, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.timing.bounds import MAX_TICKS_PER_ROW
from sampletones_player.specification.registers import (
    APU_STATUS,
    DMC_DIRECT_LOAD,
    PULSE1_CONTROL,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
)
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.markers import row_marker
from sampletones_tools.tracker_playback.targets.famitracker.trace import DriverWrite, recorded_trace
from sampletones_tools.tracker_playback.trace.sound import TickPosition

ENABLED: Final[RegisterWrite] = RegisterWrite(APU_STATUS, 0x0F)
LOUD: Final[RegisterWrite] = RegisterWrite(PULSE1_CONTROL, 0xBF)
QUIET: Final[RegisterWrite] = RegisterWrite(PULSE1_CONTROL, 0xB4)
TIMER: Final[Tuple[RegisterWrite, RegisterWrite]] = (
    RegisterWrite(PULSE1_TIMER_LOW, 0xAB),
    RegisterWrite(PULSE1_TIMER_HIGH, 0x01),
)


def marker(row_index: int) -> RegisterWrite:
    return RegisterWrite(DMC_DIRECT_LOAD, row_marker(row_index))


class ScriptedCalls:
    """Routines answering with the writes a case scripts, one play call after another, then nothing."""

    def __init__(
        self,
        initialization: Tuple[RegisterWrite, ...],
        play_calls: Sequence[Tuple[RegisterWrite, ...]],
    ) -> None:
        self._initialization = initialization
        self._play_calls: List[Tuple[RegisterWrite, ...]] = list(play_calls)

    def initialize(self) -> Tuple[RegisterWrite, ...]:
        return self._initialization

    def play(self) -> Tuple[RegisterWrite, ...]:
        return self._play_calls.pop(0) if self._play_calls else ()


class TestSplittingThePlayCalls:
    """A song of one frame and two rows, the first row lasting two ticks and the second one."""

    @pytest.fixture(name="calls")
    def calls_fixture(self) -> ScriptedCalls:
        return ScriptedCalls(
            (ENABLED,),
            (
                (marker(0), *TIMER, LOUD),
                (QUIET,),
                (marker(1), LOUD),
                (marker(2),),
            ),
        )

    def test_a_tick_falls_on_the_row_its_last_marker_started(self, calls: ScriptedCalls) -> None:
        trace = recorded_trace(calls, frames=1, rows=2)

        assert [(tick.frame, tick.row) for tick in trace.ticks] == [(0, 0), (0, 0), (0, 1)]

    def test_the_pass_ends_where_the_order_comes_back_round(self, calls: ScriptedCalls) -> None:
        assert len(recorded_trace(calls, frames=1, rows=2).ticks) == 3

    def test_each_tick_keeps_the_writes_its_call_made(self, calls: ScriptedCalls) -> None:
        trace = recorded_trace(calls, frames=1, rows=2)

        assert trace.ticks[1].writes == (DriverWrite(address=QUIET.address, value=QUIET.value),)
        assert trace.initialization == (DriverWrite(address=ENABLED.address, value=ENABLED.value),)

    def test_the_channels_sound_what_the_registers_hold_on_each_tick(self, calls: ScriptedCalls) -> None:
        song = recorded_trace(calls, frames=1, rows=2).song_trace()
        pulse = song.channels[ChannelName.PULSE1]

        assert song.positions == (TickPosition(0, 0), TickPosition(0, 0), TickPosition(0, 1))
        assert [sound.volume for sound in pulse] == [0x0F, 0x04, 0x0F]
        assert {sound.period for sound in pulse} == {0x1AB}
        assert all(sound.audible for sound in pulse)


class TestTheCallsAroundTheRows:
    def test_calls_before_the_first_row_join_its_first_tick(self) -> None:
        calls = ScriptedCalls((), ((LOUD,), (marker(0), QUIET), (marker(1),)))

        (tick,) = recorded_trace(calls, frames=1, rows=1).ticks

        assert [write.address for write in tick.writes] == [PULSE1_CONTROL, DMC_DIRECT_LOAD, PULSE1_CONTROL]

    def test_a_row_marked_out_of_place_is_reported(self) -> None:
        skipped = RegisterWrite(DMC_DIRECT_LOAD, row_marker(2))
        calls = ScriptedCalls((), ((marker(0),), (skipped,)))

        with pytest.raises(FamiTrackerError, match="marked row 1"):
            recorded_trace(calls, frames=1, rows=4)

    def test_a_row_lasting_longer_than_any_project_holds_one_is_reported(self) -> None:
        calls = ScriptedCalls((), ((marker(0),),))

        with pytest.raises(FamiTrackerError, match=str(MAX_TICKS_PER_ROW)):
            recorded_trace(calls, frames=1, rows=2)
