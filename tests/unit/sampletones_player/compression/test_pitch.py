from math import nextafter
from typing import Final

import pytest

from sampletones_core.constants.general import MAX_TIMER, MIN_TIMER
from sampletones_player.compression.pitch import PITCH_COUNT, PitchTable
from sampletones_player.specification.binary import SIGNED_BYTE_LIMIT
from sampletones_player.specification.registers import (
    MAX_REGISTER_VALUE,
    TIMER_HIGH_SHIFT,
)
from sampletones_shared.constants.music import (
    LIMIT_MAX_PITCH,
    LIMIT_MIN_PITCH,
    MAX_A4_FREQUENCY,
    MIN_A4_FREQUENCY,
)
from sampletones_shared.music import Tuning

TUNING: Final[Tuning] = Tuning()
LOWEST_TUNING: Final[Tuning] = Tuning(a4_frequency=nextafter(MIN_A4_FREQUENCY, MAX_A4_FREQUENCY))
HIGHEST_TUNING: Final[Tuning] = Tuning(a4_frequency=nextafter(MAX_A4_FREQUENCY, MIN_A4_FREQUENCY))


class TestThePitchTableNamesEveryPitchAProjectSounds:
    """A plane names a pitch by its distance above the lowest one the project reaches."""

    def test_the_table_spans_the_pitches_the_project_offers(self) -> None:
        table = PitchTable.from_tuning(TUNING)
        assert len(table.timers) == PITCH_COUNT == LIMIT_MAX_PITCH - LIMIT_MIN_PITCH + 1

    def test_every_timer_resolves_back_to_an_index_sounding_it(self) -> None:
        """Pitches clamped to the same divider sound alike, so one index stands for them."""
        table = PitchTable.from_tuning(TUNING)
        for timer in table.timers:
            named = table.nearest[timer]
            assert (table.timers[named.pitch], named.offset) == (timer, 0)

    def test_a_pitch_and_its_index_name_each_other(self) -> None:
        table = PitchTable.from_tuning(TUNING)
        for pitch in range(LIMIT_MIN_PITCH, LIMIT_MAX_PITCH + 1):
            assert table.pitch(table.index(pitch)) == pitch

    def test_a_pitch_beyond_the_table_names_no_index(self) -> None:
        with pytest.raises(ValueError):
            PitchTable.from_tuning(TUNING).index(LIMIT_MAX_PITCH + 1)

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


class TestEveryDividerReachesAPlane:
    """A bent tick sounds a divider the table may hold nowhere, so each is named as an index and
    the bend left over, and the bend must fit the signed byte its plane holds.
    """

    @pytest.mark.parametrize(
        "tuning",
        [LOWEST_TUNING, TUNING, HIGHEST_TUNING],
        ids=lambda tuning: f"a4_{tuning.a4_frequency:g}",
    )
    def test_every_divider_the_register_holds_names_a_bend_a_byte_states(self, tuning: Tuning) -> None:
        table = PitchTable.from_tuning(tuning)
        for divider in range(MIN_TIMER, MAX_TIMER + 1):
            named = table.nearest[divider]
            assert table.timers[named.pitch] + named.offset == divider
            assert -SIGNED_BYTE_LIMIT <= named.offset < SIGNED_BYTE_LIMIT
