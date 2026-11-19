from typing import Final

from sampletones_player.specification.registers import APU_STATUS, PULSE1_CONTROL
from sampletones_tools.player.trace.write import RegisterWrite
from sampletones_tools.tracker_playback.trace.registers import POWER_UP_VALUE, ChipRegisters

FIRST_VALUE: Final[int] = 0x3F
SECOND_VALUE: Final[int] = 0x30


class TestChipRegisters:
    def test_a_register_never_written_stands_at_the_power_up_value(self) -> None:
        assert ChipRegisters.power_up().value(APU_STATUS) == POWER_UP_VALUE

    def test_a_register_keeps_the_last_value_written_to_it(self) -> None:
        registers = ChipRegisters.power_up().written(
            (
                RegisterWrite(PULSE1_CONTROL, FIRST_VALUE),
                RegisterWrite(PULSE1_CONTROL, SECOND_VALUE),
            )
        )

        assert registers.value(PULSE1_CONTROL) == SECOND_VALUE

    def test_writes_lay_over_what_earlier_writes_left(self) -> None:
        earlier = ChipRegisters.power_up().written((RegisterWrite(PULSE1_CONTROL, FIRST_VALUE),))

        later = earlier.written((RegisterWrite(APU_STATUS, SECOND_VALUE),))

        assert (later.value(PULSE1_CONTROL), later.value(APU_STATUS)) == (FIRST_VALUE, SECOND_VALUE)
        assert earlier.value(APU_STATUS) == POWER_UP_VALUE


class TestARunFoldedTickByTick:
    """Each tick plays the registers the setup and every tick before it left, its own writes over them."""

    def test_each_tick_carries_what_the_ticks_before_left(self) -> None:
        setup = (RegisterWrite(APU_STATUS, FIRST_VALUE),)
        ticks = ((RegisterWrite(PULSE1_CONTROL, FIRST_VALUE),), (), (RegisterWrite(PULSE1_CONTROL, SECOND_VALUE),))

        folded = ChipRegisters.fold(setup, ticks)

        assert [registers.value(PULSE1_CONTROL) for registers in folded] == [FIRST_VALUE, FIRST_VALUE, SECOND_VALUE]
        assert all(registers.value(APU_STATUS) == FIRST_VALUE for registers in folded)

    def test_a_run_of_no_ticks_folds_to_none(self) -> None:
        assert ChipRegisters.fold((RegisterWrite(APU_STATUS, FIRST_VALUE),), ()) == ()

    def test_the_ticks_may_be_read_once(self) -> None:
        folded = ChipRegisters.fold((), iter([(RegisterWrite(APU_STATUS, SECOND_VALUE),)]))
        assert folded[0].value(APU_STATUS) == SECOND_VALUE

    def test_a_tick_writing_one_register_twice_keeps_the_later_value(self) -> None:
        tick = (RegisterWrite(PULSE1_CONTROL, FIRST_VALUE), RegisterWrite(PULSE1_CONTROL, SECOND_VALUE))
        assert ChipRegisters.fold((), (tick,))[0].value(PULSE1_CONTROL) == SECOND_VALUE
