from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_player.specification.registers import (
    APU_FRAME_COUNTER,
    APU_STATUS,
    CHANNELS_ENABLED,
    FIRST_CHANNEL_REGISTER,
    FRAME_COUNTER_SEQUENCE,
    LAST_CHANNEL_REGISTER,
    PULSE1_CONTROL,
    PULSE1_SWEEP,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
    PULSE2_SWEEP,
    REGISTERS_WRITTEN_ON_CHANGE,
    SILENCED_REGISTER,
    SWEEP_DISABLED,
    TRIANGLE_TIMER_HIGH,
)
from sampletones_player.trace.trace import RegisterTrace
from sampletones_player.trace.write import RegisterWrite
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseAutolabelTestCase
from tests.suite.player import (
    PLAYER_FULL_VOLUME,
    PLAYER_OCTAVE_UP_TIMER,
    PLAYER_REFERENCE_TIMER,
    PLAYER_SILENT_VOLUME,
    player_song,
    pulse_tick,
    resting_streams,
)

NTSC_FREQUENCY: Final[int] = 60
HALF_RATE_FREQUENCY: Final[int] = 30
WRITES_PER_TICK: Final[int] = 11

SOUNDING: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_REFERENCE_TIMER)
RESTING: Final = pulse_tick(PLAYER_SILENT_VOLUME, 0, PLAYER_REFERENCE_TIMER)
OCTAVE_UP: Final = pulse_tick(PLAYER_FULL_VOLUME, 0, PLAYER_OCTAVE_UP_TIMER)


def addresses(writes: Tuple[RegisterWrite, ...]) -> Tuple[int, ...]:
    return tuple(write.address for write in writes)


class TestInitialisation:
    """The init routine leaves a silent console enabled and sounding the song's first tick."""

    SONG: Final = player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=None)

    @property
    def initialisation(self) -> Tuple[RegisterWrite, ...]:
        return RegisterTrace.from_song(self.SONG, play_calls=0).initialisation

    def test_every_channel_register_is_cleared_first(self) -> None:
        cleared = self.initialisation[: LAST_CHANNEL_REGISTER - FIRST_CHANNEL_REGISTER + 1]
        assert addresses(cleared) == tuple(range(FIRST_CHANNEL_REGISTER, LAST_CHANNEL_REGISTER + 1))
        assert all(write.value == SILENCED_REGISTER for write in cleared)

    def test_the_channels_are_enabled(self) -> None:
        assert RegisterWrite(APU_STATUS, CHANNELS_ENABLED) in self.initialisation

    def test_the_frame_counter_runs_without_an_interrupt(self) -> None:
        assert RegisterWrite(APU_FRAME_COUNTER, FRAME_COUNTER_SEQUENCE) in self.initialisation

    def test_both_sweep_units_are_disabled(self) -> None:
        assert RegisterWrite(PULSE1_SWEEP, SWEEP_DISABLED) in self.initialisation
        assert RegisterWrite(PULSE2_SWEEP, SWEEP_DISABLED) in self.initialisation

    def test_the_sweep_survives_the_clearing_pass(self) -> None:
        sweeps = [write.value for write in self.initialisation if write.address == PULSE1_SWEEP]
        assert sweeps[-1] == SWEEP_DISABLED

    def test_the_first_tick_sounds_from_initialisation(self) -> None:
        first_tick = self.initialisation[-WRITES_PER_TICK:]
        assert len(first_tick) == WRITES_PER_TICK
        assert first_tick[0] == RegisterWrite(PULSE1_CONTROL, self.SONG.streams.pulse1[0].control)

    def test_the_first_tick_writes_the_registers_that_reset_a_channel(self) -> None:
        first_tick = self.initialisation[-WRITES_PER_TICK:]
        assert REGISTERS_WRITTEN_ON_CHANGE.issubset(set(addresses(first_tick)))


class TestChangeSuppression:
    """The three registers that disturb a running channel are written only where they change."""

    def test_a_held_pitch_leaves_the_timer_high_byte_alone(self) -> None:
        song = player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=2)
        assert PULSE1_TIMER_HIGH not in addresses(trace.play_calls[1])

    def test_a_held_pitch_still_writes_the_timer_low_byte(self) -> None:
        song = player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=2)
        assert PULSE1_TIMER_LOW in addresses(trace.play_calls[1])

    def test_a_pitch_change_writes_the_timer_high_byte(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=2)
        assert PULSE1_TIMER_HIGH in addresses(trace.play_calls[1])

    def test_a_returning_pitch_writes_the_timer_high_byte_again(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP, SOUNDING)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=3)
        assert PULSE1_TIMER_HIGH in addresses(trace.play_calls[2])

    def test_an_unchanging_channel_never_rewrites_its_high_byte(self) -> None:
        song = player_song(resting_streams((SOUNDING, RESTING, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=3)
        rewritten = [write for writes in trace.play_calls for write in writes if write.address == TRIANGLE_TIMER_HIGH]
        assert rewritten == []


class TestPlaySchedule(BaseTestSuite):
    """Which calls write and which leave the console alone, across the stream rates."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseAutolabelTestCase):
        expected: Tuple[bool, ...]
        nes_frequency: int

        @property
        def label(self) -> str:
            return f"{self.nes_frequency}hz"

    test_cases: Tuple[TestCase, ...] = (
        TestCase(nes_frequency=NTSC_FREQUENCY, expected=(False, True, True, True)),
        TestCase(nes_frequency=HALF_RATE_FREQUENCY, expected=(False, False, True, False)),
        TestCase(nes_frequency=15, expected=(False, False, False, False)),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_only_the_calls_that_advance_write(self, test_case: TestCase) -> None:
        song = player_song(
            resting_streams((SOUNDING, OCTAVE_UP, RESTING, RESTING)),
            test_case.nes_frequency,
            loop_tick=None,
        )
        trace = RegisterTrace.from_song(song, play_calls=len(test_case.expected))
        assert tuple(bool(writes) for writes in trace.play_calls) == test_case.expected

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_a_call_that_writes_touches_every_channel(self, test_case: TestCase) -> None:
        song = player_song(
            resting_streams((SOUNDING, OCTAVE_UP, RESTING, RESTING)),
            test_case.nes_frequency,
            loop_tick=None,
        )
        trace = RegisterTrace.from_song(song, play_calls=len(test_case.expected))
        for writes in trace.play_calls:
            assert not writes or PULSE1_CONTROL in addresses(writes)


class TestEndOfSong:
    """A song that ends stops writing, and one that repeats keeps playing from its loop tick."""

    def test_a_song_without_a_loop_stops_writing(self) -> None:
        song = player_song(resting_streams((SOUNDING, RESTING)), NTSC_FREQUENCY, loop_tick=None)
        trace = RegisterTrace.from_song(song, play_calls=6)
        assert all(writes == () for writes in trace.play_calls[3:])

    def test_a_song_with_a_loop_keeps_writing(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=0)
        trace = RegisterTrace.from_song(song, play_calls=6)
        assert all(writes != () for writes in trace.play_calls[1:])

    def test_a_loop_replays_the_ticks_it_returns_to(self) -> None:
        song = player_song(resting_streams((SOUNDING, OCTAVE_UP)), NTSC_FREQUENCY, loop_tick=0)
        trace = RegisterTrace.from_song(song, play_calls=4)
        assert addresses(trace.play_calls[1]) == addresses(trace.play_calls[3])

    def test_no_calls_produce_no_writes(self) -> None:
        song = player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)
        assert RegisterTrace.from_song(song, play_calls=0).play_calls == ()

    def test_a_negative_call_count_raises(self) -> None:
        song = player_song(resting_streams((SOUNDING,)), NTSC_FREQUENCY, loop_tick=None)
        with pytest.raises(ValueError):
            RegisterTrace.from_song(song, play_calls=-1)
