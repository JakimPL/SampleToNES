from dataclasses import dataclass
from typing import Final, List, Tuple

import pytest

from sampletones_core.formats.bitphase.specification.chip import (
    CPU_FREQUENCIES,
    DEFAULT_A4_TUNING,
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
    TUNING_A4_INDEX,
    TUNING_TABLE_LENGTH,
    ChipVariant,
)
from sampletones_core.formats.bitphase.tuning import generate_tuning_table

BITPHASE_NTSC_TABLE: Final[Tuple[int, ...]] = (
    2047, 2047, 2047, 2047, 2047, 2047, 2047, 2047, 2047, 2034, 1920, 1812,
    1710, 1614, 1524, 1438, 1357, 1281, 1209, 1141, 1077, 1017, 960, 906,
    855, 807, 762, 719, 679, 641, 605, 571, 539, 508, 480, 453,
    428, 404, 381, 360, 339, 320, 302, 285, 269, 254, 240, 226,
    214, 202, 190, 180, 170, 160, 151, 143, 135, 127, 120, 113,
    107, 101, 95, 90, 85, 80, 76, 71, 67, 64, 60, 57,
    53, 50, 48, 45, 42, 40, 38, 36, 34, 32, 30, 28,
    27, 25, 24, 22, 21, 20, 19, 18, 17, 16, 15, 14,
)  # fmt: skip


@dataclass
class PeriodCase:
    variant: ChipVariant
    index: int
    period: int


VARIANT_CASES: List[PeriodCase] = [
    PeriodCase(variant=ChipVariant.NTSC, index=9, period=2034),
    PeriodCase(variant=ChipVariant.NTSC, index=45, period=254),
    PeriodCase(variant=ChipVariant.NTSC, index=95, period=14),
    PeriodCase(variant=ChipVariant.PAL, index=9, period=1889),
    PeriodCase(variant=ChipVariant.PAL, index=45, period=236),
    PeriodCase(variant=ChipVariant.PAL, index=95, period=13),
    PeriodCase(variant=ChipVariant.DENDY, index=9, period=2015),
    PeriodCase(variant=ChipVariant.DENDY, index=45, period=252),
    PeriodCase(variant=ChipVariant.DENDY, index=95, period=14),
]

SLOW_CLOCK: Final[int] = 1000
RAISED_A4_TUNING: Final[float] = 432.0
RAISED_A4_PERIOD: Final[int] = 259
NARROW_TIMER_LIMIT: Final[int] = 255


@pytest.fixture(name="ntsc_table")
def ntsc_table_fixture() -> Tuple[int, ...]:
    return generate_tuning_table(
        CPU_FREQUENCIES[ChipVariant.NTSC],
        a4_tuning=DEFAULT_A4_TUNING,
    )


class TestTheTableMatchesBitphase:
    """The tuning table is the contract with Bitphase: the tracker derives its own from
    the same settings, so a document whose table differs plays at a different pitch than
    the reconstruction it came from. These numbers come from Bitphase's own generator.
    """

    def test_the_ntsc_table_equals_the_one_bitphase_derives(self, ntsc_table: Tuple[int, ...]) -> None:
        assert ntsc_table == BITPHASE_NTSC_TABLE

    @pytest.mark.parametrize("case", VARIANT_CASES, ids=lambda case: f"{case.variant}-{case.index}")
    def test_each_system_clock_yields_bitphase_periods(self, case: PeriodCase) -> None:
        table = generate_tuning_table(CPU_FREQUENCIES[case.variant], a4_tuning=DEFAULT_A4_TUNING)
        assert table[case.index] == case.period

    def test_a_shifted_concert_pitch_moves_the_whole_table(self) -> None:
        table = generate_tuning_table(
            CPU_FREQUENCIES[ChipVariant.NTSC],
            a4_tuning=RAISED_A4_TUNING,
        )
        assert table[TUNING_A4_INDEX] == RAISED_A4_PERIOD


class TestTableShape:
    def test_the_table_covers_every_note_index(self, ntsc_table: Tuple[int, ...]) -> None:
        assert len(ntsc_table) == TUNING_TABLE_LENGTH

    def test_a_rising_note_index_shortens_the_period(self, ntsc_table: Tuple[int, ...]) -> None:
        assert all(later <= earlier for earlier, later in zip(ntsc_table, ntsc_table[1:]))

    @pytest.mark.parametrize("variant", list(ChipVariant))
    def test_every_period_fits_the_channel_timer(self, variant: ChipVariant) -> None:
        table = generate_tuning_table(CPU_FREQUENCIES[variant], a4_tuning=DEFAULT_A4_TUNING)
        assert all(MIN_TUNING_PERIOD <= period <= MAX_TUNING_PERIOD for period in table)

    def test_a_clock_too_slow_for_the_top_notes_holds_the_shortest_period(self) -> None:
        table = generate_tuning_table(SLOW_CLOCK, a4_tuning=DEFAULT_A4_TUNING)
        assert table[-1] == MIN_TUNING_PERIOD

    def test_a_narrower_timer_holds_the_longest_period(self) -> None:
        table = generate_tuning_table(
            CPU_FREQUENCIES[ChipVariant.NTSC],
            a4_tuning=DEFAULT_A4_TUNING,
            max_period=NARROW_TIMER_LIMIT,
        )
        assert max(table) == NARROW_TIMER_LIMIT
