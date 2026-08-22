from typing import Final

from sampletones_player.compression.pitch import PITCH_COUNT, PitchTable
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    TIMER_HIGH_SHIFT,
)
from sampletones_shared.constants.music import LIMIT_MAX_PITCH, LIMIT_MIN_PITCH
from sampletones_shared.music import Tuning

TUNING: Final[Tuning] = Tuning()


class TestThePitchTableNamesEveryPitchAProjectSounds:
    """A plane names a pitch by its distance above the lowest one the project reaches."""

    def test_the_table_spans_the_pitches_the_project_offers(self) -> None:
        table = PitchTable.from_tuning(TUNING)
        assert len(table.timers) == PITCH_COUNT == LIMIT_MAX_PITCH - LIMIT_MIN_PITCH + 1

    def test_every_timer_resolves_back_to_an_index_sounding_it(self) -> None:
        """Pitches clamped to the same divider sound alike, so one index stands for them."""
        table = PitchTable.from_tuning(TUNING)
        indices = table.indices
        for timer in table.timers:
            assert table.timers[indices[timer]] == timer

    def test_a_higher_index_never_sounds_a_slower_divider(self) -> None:
        table = PitchTable.from_tuning(TUNING)
        for timer, following in zip(table.timers, table.timers[1:]):
            assert following <= timer

    def test_the_driver_reads_the_low_bytes_then_the_high_bytes(self) -> None:
        table = PitchTable.from_tuning(TUNING)
        data = table.data
        assert len(data) == 2 * PITCH_COUNT
        for index, timer in enumerate(table.timers):
            assert data[index] == timer & MAX_REGISTER_VALUE
            assert data[PITCH_COUNT + index] == timer >> TIMER_HIGH_SHIFT

    def test_a_retuned_table_moves_the_dividers(self) -> None:
        standard = PitchTable.from_tuning(TUNING)
        retuned = PitchTable.from_tuning(Tuning(a4_frequency=432.0))
        assert retuned.timers != standard.timers
