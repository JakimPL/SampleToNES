import json
from dataclasses import dataclass
from typing import Any, Dict, Final, List, Sequence, Tuple

import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_player.specification.registers import (
    APU_STATUS,
    DUTY_CYCLE_SHIFT,
    MAX_REGISTER_VALUE,
    NOISE_CONTROL,
    NOISE_PERIOD,
    PULSE1_CONTROL,
    PULSE1_TIMER_HIGH,
    PULSE1_TIMER_LOW,
    PULSE2_CONTROL,
    SUSTAINED_LEVEL,
    TIMER_HIGH_SHIFT,
    TRIANGLE_LINEAR_COUNTER,
    TRIANGLE_TIMER_HIGH,
    TRIANGLE_TIMER_LOW,
)
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.targets.bitphase.trace import (
    UNIT_STATUS_BITS,
    EmulatorUnit,
    UnitWrite,
    read_engine_trace,
)
from sampletones_tools.tracker_playback.trace.sound import ABSENT_REGISTER, ChannelSound, TickPosition
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

PULSE_STATUS: Final[int] = 0x03
TRIANGLE_NOISE_STATUS: Final[int] = 0x0C
EVERY_STATUS_BIT: Final[int] = 0x1F
LENGTH_INDEX_BITS: Final[int] = 0x78
PULSE_TIMER: Final[int] = 427
PULSE_LEVEL: Final[int] = 15
PULSE_DUTY: Final[int] = 2
TRIANGLE_TIMER: Final[int] = 854
NOISE_LEVEL: Final[int] = 14
NOISE_REGISTER_PERIOD: Final[int] = 9
SOUNDING_PULSE: Final[int] = (PULSE_DUTY << DUTY_CYCLE_SHIFT) | SUSTAINED_LEVEL | PULSE_LEVEL
SOUNDING_TRIANGLE: Final[int] = 0xFF
SOUNDING_NOISE: Final[int] = SUSTAINED_LEVEL | NOISE_LEVEL

Write = Tuple[EmulatorUnit, int, int]

ENABLING: Final[Tuple[Write, ...]] = (
    (EmulatorUnit.APU, APU_STATUS, PULSE_STATUS),
    (EmulatorUnit.DMC, APU_STATUS, TRIANGLE_NOISE_STATUS),
)
PULSE_WRITES: Final[Tuple[Write, ...]] = (
    (EmulatorUnit.APU, PULSE1_CONTROL, SOUNDING_PULSE),
    (EmulatorUnit.APU, PULSE1_TIMER_LOW, PULSE_TIMER & MAX_REGISTER_VALUE),
    (EmulatorUnit.APU, PULSE1_TIMER_HIGH, LENGTH_INDEX_BITS | (PULSE_TIMER >> TIMER_HIGH_SHIFT)),
)
EVERY_CHANNEL_SOUNDING: Final[Tuple[Write, ...]] = (
    *ENABLING,
    *PULSE_WRITES,
    (EmulatorUnit.APU, PULSE2_CONTROL, SOUNDING_PULSE),
    (EmulatorUnit.DMC, TRIANGLE_LINEAR_COUNTER, SOUNDING_TRIANGLE),
    (EmulatorUnit.DMC, TRIANGLE_TIMER_LOW, TRIANGLE_TIMER & MAX_REGISTER_VALUE),
    (EmulatorUnit.DMC, TRIANGLE_TIMER_HIGH, LENGTH_INDEX_BITS | (TRIANGLE_TIMER >> TIMER_HIGH_SHIFT)),
    (EmulatorUnit.DMC, NOISE_CONTROL, SOUNDING_NOISE),
    (EmulatorUnit.DMC, NOISE_PERIOD, NOISE_REGISTER_PERIOD),
)


def _tick(*writes: Write, frame: int = 0, row: int = 0) -> Dict[str, Any]:
    return {
        "frame": frame,
        "row": row,
        "writes": [{"unit": unit.value, "address": address, "value": value} for unit, address, value in writes],
    }


def _trace_text(ticks: Sequence[Dict[str, Any]]) -> str:
    return json.dumps({"ticks": list(ticks)})


def _audible(ticks: Sequence[Dict[str, Any]]) -> Dict[ChannelName, List[bool]]:
    trace = read_engine_trace(_trace_text(ticks))
    return {channel: [sound.audible for sound in sounds] for channel, sounds in trace.channels.items()}


class TestUnitWrite(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        unit: EmulatorUnit
        status: int
        value: int
        expected: int

    test_cases: Tuple[TestCase, ...] = (
        TestCase(
            label="the pulse unit keeps the others' bits", unit=EmulatorUnit.APU, status=0x0C, value=0x1F, expected=0x0F
        ),
        TestCase(
            label="the pulse unit clears its own bits", unit=EmulatorUnit.APU, status=0x0F, value=0x00, expected=0x0C
        ),
        TestCase(
            label="the dmc unit keeps the pulse bits", unit=EmulatorUnit.DMC, status=0x03, value=0x03, expected=0x03
        ),
        TestCase(label="the dmc unit sets its own bits", unit=EmulatorUnit.DMC, status=0x03, value=0x1C, expected=0x1F),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_a_status_write_reaches_the_bits_of_the_channels_its_unit_plays(self, test_case: TestCase) -> None:
        write = UnitWrite(unit=test_case.unit, address=APU_STATUS, value=test_case.value)

        assert write.chip_write(test_case.status) == RegisterWrite(APU_STATUS, test_case.expected)

    def test_the_units_share_the_status_register_between_them(self) -> None:
        assert UNIT_STATUS_BITS[EmulatorUnit.APU] | UNIT_STATUS_BITS[EmulatorUnit.DMC] == EVERY_STATUS_BIT
        assert not UNIT_STATUS_BITS[EmulatorUnit.APU] & UNIT_STATUS_BITS[EmulatorUnit.DMC]

    @pytest.mark.parametrize("unit", tuple(EmulatorUnit), ids=str)
    def test_a_channel_register_write_reaches_the_chip_as_it_is(self, unit: EmulatorUnit) -> None:
        write = UnitWrite(unit=unit, address=NOISE_CONTROL, value=SOUNDING_NOISE)

        assert write.chip_write(EVERY_STATUS_BIT) == RegisterWrite(NOISE_CONTROL, SOUNDING_NOISE)


class TestReadEngineTrace:
    def test_each_tick_keeps_the_frame_and_row_bitphase_played_it_at(self) -> None:
        trace = read_engine_trace(_trace_text((_tick(frame=2, row=5),)))

        assert trace.positions == (TickPosition(frame=2, row=5),)
        assert set(trace.channels) == set(ChannelName.items())

    def test_every_channel_is_read_from_the_registers_the_engine_wrote(self) -> None:
        trace = read_engine_trace(_trace_text((_tick(*EVERY_CHANNEL_SOUNDING),)))

        assert trace.channels[ChannelName.PULSE1] == (
            ChannelSound(audible=True, period=PULSE_TIMER, volume=PULSE_LEVEL, held=True, timbre=PULSE_DUTY),
        )
        assert trace.channels[ChannelName.TRIANGLE] == (
            ChannelSound(
                audible=True, period=TRIANGLE_TIMER, volume=ABSENT_REGISTER, held=True, timbre=ABSENT_REGISTER
            ),
        )
        assert trace.channels[ChannelName.NOISE] == (
            ChannelSound(audible=True, period=NOISE_REGISTER_PERIOD, volume=NOISE_LEVEL, held=True, timbre=0),
        )

    def test_a_register_written_on_one_tick_stands_on_the_ticks_after(self) -> None:
        trace = read_engine_trace(_trace_text((_tick(*ENABLING, *PULSE_WRITES), _tick(), _tick())))

        assert len(set(trace.channels[ChannelName.PULSE1])) == 1
        assert trace.channels[ChannelName.PULSE1][-1].audible

    def test_each_unit_enables_the_channels_it_plays(self) -> None:
        audible = _audible(
            (
                _tick(*EVERY_CHANNEL_SOUNDING),
                _tick((EmulatorUnit.DMC, APU_STATUS, 0x00)),
                _tick((EmulatorUnit.APU, APU_STATUS, 0x00), (EmulatorUnit.DMC, APU_STATUS, TRIANGLE_NOISE_STATUS)),
            )
        )

        assert audible == {
            ChannelName.PULSE1: [True, True, False],
            ChannelName.PULSE2: [True, True, False],
            ChannelName.TRIANGLE: [True, False, True],
            ChannelName.NOISE: [True, False, True],
        }

    @pytest.mark.parametrize(
        "write",
        (
            {"unit": "apu", "address": 0x3FFF, "value": 0},
            {"unit": "apu", "address": APU_STATUS, "value": 0x100},
            {"unit": "mmc5", "address": APU_STATUS, "value": 0},
        ),
        ids=("below the apu", "wider than a byte", "no unit of the emulator"),
    )
    def test_a_write_the_script_never_records_is_refused(self, write: Dict[str, Any]) -> None:
        with pytest.raises(ValidationError):
            read_engine_trace(json.dumps({"ticks": [{"frame": 0, "row": 0, "writes": [write]}]}))
