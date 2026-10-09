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
