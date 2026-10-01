from typing import Final, Tuple

import pytest

from sampletones_player.specification.nsf import PAL_REGION_FLAG, PROGRAM_START
from sampletones_player.specification.registers import APU_STATUS, PULSE1_CONTROL
from sampletones_tools.console.cartridge import BANK_SIZE, FIRST_BANK_REGISTER
from sampletones_tools.console.errors import RoutineOverrunError
from sampletones_tools.console.header import PAL_MACHINE
from sampletones_tools.console.machine import Console
from sampletones_tools.player.trace.write import RegisterWrite
from tests.unit.sampletones_tools.console.files import (
    INIT,
    JUMP,
    LOAD_ABSOLUTE,
    LOAD_IMMEDIATE,
    PLAY,
    RETURN,
    STORE_ACCUMULATOR,
    STORE_INDEX,
    NSFFile,
    absolute,
    bank_offset,
)

SONG_REGISTER: Final[int] = 0x4002
MACHINE_REGISTER: Final[int] = 0x4003
CHANNELS_ON: Final[int] = 0x0F
PLAYED: Final[int] = 0x3F
SECOND_SLOT: Final[int] = PROGRAM_START + BANK_SIZE
BANK_MARKS: Final[Tuple[int, int]] = (0x77, 0x55)
STEP_BUDGET: Final[int] = 1000
ENDLESS_BUDGET: Final[int] = 50

INIT_PROGRAM: Final[Tuple[int, ...]] = (
    STORE_ACCUMULATOR,
    *absolute(SONG_REGISTER),
    STORE_INDEX,
    *absolute(MACHINE_REGISTER),
    LOAD_IMMEDIATE,
    CHANNELS_ON,
    STORE_ACCUMULATOR,
    *absolute(APU_STATUS),
    RETURN,
)
PLAY_PROGRAM: Final[Tuple[int, ...]] = (
    LOAD_IMMEDIATE,
    PLAYED,
    STORE_ACCUMULATOR,
    *absolute(PULSE1_CONTROL),
    RETURN,
)
SWITCHING_INIT: Final[Tuple[int, ...]] = (
    LOAD_IMMEDIATE,
    1,
    STORE_ACCUMULATOR,
    *absolute(FIRST_BANK_REGISTER + 1),
    RETURN,
)
READING_PLAY: Final[Tuple[int, ...]] = (
    LOAD_ABSOLUTE,
    *absolute(SECOND_SLOT),
    STORE_ACCUMULATOR,
    *absolute(PULSE1_CONTROL),
    RETURN,
)
ENDLESS_INIT: Final[Tuple[int, ...]] = (JUMP, *absolute(INIT))
INIT_WRITES: Final[Tuple[RegisterWrite, ...]] = (
    RegisterWrite(SONG_REGISTER, 1),
    RegisterWrite(MACHINE_REGISTER, PAL_MACHINE),
    RegisterWrite(APU_STATUS, CHANNELS_ON),
)


def _console(file: NSFFile) -> Console:
    return Console(file.data, step_budget=STEP_BUDGET)


@pytest.fixture(name="console")
def console_fixture() -> Console:
    """A PAL file holding three songs and starting on the second, whose routines write what they are given."""
    return _console(
        NSFFile(
            region=PAL_REGION_FLAG,
            songs=3,
            first_song=2,
            program={INIT - PROGRAM_START: INIT_PROGRAM, PLAY - PROGRAM_START: PLAY_PROGRAM},
        )
    )


@pytest.fixture(name="banked")
def banked_fixture() -> Console:
    """A banked file whose second slot starts on bank 2, which its init routine switches to bank 1."""
    return _console(
        NSFFile(
            banks=(0, 2, 0, 0, 0, 0, 0, 0),
            program={
                INIT - PROGRAM_START: SWITCHING_INIT,
                PLAY - PROGRAM_START: READING_PLAY,
                bank_offset(1): (BANK_MARKS[0],),
                bank_offset(2): (BANK_MARKS[1],),
            },
        )
    )


class TestRoutines:
    def test_init_is_handed_the_first_song_and_the_machine(self, console: Console) -> None:
        assert console.initialize() == INIT_WRITES

    def test_a_play_call_answers_with_its_own_writes_alone(self, console: Console) -> None:
        console.initialize()

        assert console.play() == (RegisterWrite(PULSE1_CONTROL, PLAYED),)

    def test_a_trace_holds_the_initialization_and_every_play_call(self, console: Console) -> None:
        trace = console.trace(3)

        assert trace.initialization == INIT_WRITES
        assert trace.play_calls == ((RegisterWrite(PULSE1_CONTROL, PLAYED),),) * 3

    def test_a_routine_that_never_returns_is_stopped(self) -> None:
        console = Console(NSFFile(program={INIT - PROGRAM_START: ENDLESS_INIT}).data, step_budget=ENDLESS_BUDGET)

        with pytest.raises(RoutineOverrunError):
            console.initialize()


class TestBankSwitching:
    def test_a_slot_plays_the_bank_the_header_names_until_the_program_switches_it(self, banked: Console) -> None:
        assert banked.play() == (RegisterWrite(PULSE1_CONTROL, BANK_MARKS[1]),)

    def test_a_switch_maps_the_bank_the_program_names(self, banked: Console) -> None:
        banked.initialize()

        assert banked.play() == (RegisterWrite(PULSE1_CONTROL, BANK_MARKS[0]),)
