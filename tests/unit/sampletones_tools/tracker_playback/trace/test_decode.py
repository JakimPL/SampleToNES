from dataclasses import dataclass
from typing import Final, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_player.specification.registers import (
    APU_STATUS,
    CHANNELS_ENABLED,
    CONSTANT_VOLUME,
    DUTY_CYCLE_SHIFT,
    LENGTH_COUNTER_HALT,
    MAX_REGISTER_VALUE,
    NOISE_CONTROL,
    NOISE_MODE_SHIFT,
    NOISE_PERIOD,
    PULSE1_CONTROL,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
    PULSE2_CONTROL,
    PULSE2_TIMER_HIGH,
    PULSE2_TIMER_LOW,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_COUNTER_CONTROL,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_TIMER_HIGH,
    TRIANGLE_TIMER_LOW,
)
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.trace.decode import (
    CHANNEL_STATUS_BITS,
    LINEAR_COUNTER_RELOAD,
    channel_sound,
    song_trace,
)
from sampletones_tools.tracker_playback.trace.registers import ChipRegisters
from sampletones_tools.tracker_playback.trace.sound import ABSENT_REGISTER, ChannelSound, TickPosition
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TIMER: Final[int] = 0x1AB
LENGTH_INDEX_BITS: Final[int] = 0xF8
TIMER_LOW: Final[int] = TIMER & MAX_REGISTER_VALUE
TIMER_HIGH: Final[int] = LENGTH_INDEX_BITS | (TIMER >> TIMER_HIGH_SHIFT)
DUTY: Final[int] = 1
LEVEL: Final[int] = 9
NOISE_REGISTER_PERIOD: Final[int] = 6
SOUNDING_PULSE: Final[int] = (DUTY << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | LEVEL
SOUNDING_TRIANGLE: Final[int] = TRIANGLE_COUNTER_CONTROL | LINEAR_COUNTER_RELOAD
SOUNDING_NOISE: Final[int] = SUSTAINED_LEVEL | LEVEL
SHORT_NOISE_PERIOD: Final[int] = (1 << NOISE_MODE_SHIFT) | NOISE_REGISTER_PERIOD


def _registers(
    *writes: Tuple[int, int],
    status: int = CHANNELS_ENABLED,
) -> ChipRegisters:
    return ChipRegisters.power_up().written(
        RegisterWrite(address, value) for address, value in ((APU_STATUS, status), *writes)
    )


def _every_channel_sounding(status: int) -> ChipRegisters:
    return _registers(
        (PULSE1_CONTROL, SOUNDING_PULSE),
        (PULSE1_TIMER_LOW, TIMER_LOW),
        (PULSE1_TIMER_HIGH, TIMER_HIGH),
        (PULSE2_CONTROL, SOUNDING_PULSE),
        (PULSE2_TIMER_LOW, TIMER_LOW),
        (PULSE2_TIMER_HIGH, TIMER_HIGH),
        (TRIANGLE_LINEAR_COUNTER, SOUNDING_TRIANGLE),
        (TRIANGLE_TIMER_LOW, TIMER_LOW),
        (TRIANGLE_TIMER_HIGH, TIMER_HIGH),
        (NOISE_CONTROL, SOUNDING_NOISE),
        (NOISE_PERIOD, SHORT_NOISE_PERIOD),
        status=status,
    )


class TestPulseSound(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channel: ChannelName
        control: int
        timer_low: int
        timer_high: int

    test_cases: Tuple[TestCase, ...] = (
        TestCase(
            label="pulse1",
            channel=ChannelName.PULSE1,
            control=PULSE1_CONTROL,
            timer_low=PULSE1_TIMER_LOW,
            timer_high=PULSE1_TIMER_HIGH,
        ),
        TestCase(
            label="pulse2",
            channel=ChannelName.PULSE2,
            control=PULSE2_CONTROL,
            timer_low=PULSE2_TIMER_LOW,
            timer_high=PULSE2_TIMER_HIGH,
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_pulse_reads_its_duty_its_level_and_its_timer_under_the_length_index(self, test_case: TestCase) -> None:
        registers = _registers(
            (test_case.control, SOUNDING_PULSE),
            (test_case.timer_low, TIMER_LOW),
            (test_case.timer_high, TIMER_HIGH),
        )

        assert channel_sound(test_case.channel, registers) == ChannelSound(
            audible=True,
            period=TIMER,
            volume=LEVEL,
            held=True,
            timbre=DUTY,
        )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_pulse_at_level_zero_is_silent(self, test_case: TestCase) -> None:
        registers = _registers((test_case.control, SUSTAINED_LEVEL))

        assert not channel_sound(test_case.channel, registers).audible

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_pulse_running_its_envelope_sounds_counted_down_from_full(self, test_case: TestCase) -> None:
        registers = _registers((test_case.control, LENGTH_COUNTER_HALT))

        sound = channel_sound(test_case.channel, registers)

        assert sound.audible
        assert not sound.held

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_constant_level_under_a_running_length_counter_is_counted_down(self, test_case: TestCase) -> None:
        registers = _registers((test_case.control, CONSTANT_VOLUME | LEVEL))

        sound = channel_sound(test_case.channel, registers)

        assert (sound.audible, sound.volume, sound.held) == (True, LEVEL, False)


class TestTriangleSound:
    def test_the_triangle_sounds_its_timer_while_its_linear_counter_reloads(self) -> None:
        registers = _registers(
            (TRIANGLE_LINEAR_COUNTER, SOUNDING_TRIANGLE),
            (TRIANGLE_TIMER_LOW, TIMER_LOW),
            (TRIANGLE_TIMER_HIGH, TIMER_HIGH),
        )

        assert channel_sound(ChannelName.TRIANGLE, registers) == ChannelSound(
            audible=True,
            period=TIMER,
            volume=ABSENT_REGISTER,
            held=True,
            timbre=ABSENT_REGISTER,
        )

    @pytest.mark.parametrize("control", (TRIANGLE_COUNTER_CONTROL, 0), ids=("held", "released"))
    def test_a_reload_of_zero_is_silent(self, control: int) -> None:
        registers = _registers((TRIANGLE_LINEAR_COUNTER, control))

        assert not channel_sound(ChannelName.TRIANGLE, registers).audible

    def test_a_clear_control_flag_counts_the_triangle_down(self) -> None:
        registers = _registers((TRIANGLE_LINEAR_COUNTER, LINEAR_COUNTER_RELOAD))

        sound = channel_sound(ChannelName.TRIANGLE, registers)

        assert sound.audible
        assert not sound.held


class TestNoiseSound:
    def test_the_noise_reads_its_level_its_period_index_and_its_mode(self) -> None:
        registers = _registers((NOISE_CONTROL, SOUNDING_NOISE), (NOISE_PERIOD, SHORT_NOISE_PERIOD))

        assert channel_sound(ChannelName.NOISE, registers) == ChannelSound(
            audible=True,
            period=NOISE_REGISTER_PERIOD,
            volume=LEVEL,
            held=True,
            timbre=1,
        )

    def test_the_noise_at_level_zero_is_silent(self) -> None:
        registers = _registers((NOISE_CONTROL, SUSTAINED_LEVEL), (NOISE_PERIOD, SHORT_NOISE_PERIOD))

        assert not channel_sound(ChannelName.NOISE, registers).audible


class TestStatusRegister:
    @pytest.mark.parametrize("channel", ChannelName.items(), ids=str)
    def test_a_channel_the_status_register_leaves_disabled_is_silent(self, channel: ChannelName) -> None:
        registers = _every_channel_sounding(CHANNELS_ENABLED & ~CHANNEL_STATUS_BITS[channel])

        assert {other: channel_sound(other, registers).audible for other in ChannelName.items()} == {
            other: other != channel for other in ChannelName.items()
        }

    def test_every_channel_is_silent_before_any_write(self) -> None:
        assert not any(channel_sound(channel, ChipRegisters.power_up()).audible for channel in ChannelName.items())


class TestSongTrace:
    def test_every_channel_is_read_on_every_tick(self) -> None:
        positions = (TickPosition(frame=0, row=0), TickPosition(frame=0, row=1))
        registers = (_every_channel_sounding(CHANNELS_ENABLED), ChipRegisters.power_up())

        trace = song_trace(positions, registers)

        assert trace.positions == positions
        assert {channel: [sound.audible for sound in sounds] for channel, sounds in trace.channels.items()} == {
            channel: [True, False] for channel in ChannelName.items()
        }

    def test_registers_for_another_number_of_ticks_are_refused(self) -> None:
        with pytest.raises(ValueError, match="2 ticks have 1"):
            song_trace((TickPosition(frame=0, row=0),) * 2, (ChipRegisters.power_up(),))
