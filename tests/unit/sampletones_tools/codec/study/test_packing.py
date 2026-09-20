from math import ceil
from typing import Final, FrozenSet, Tuple

import pytest

from sampletones_core.constants.general import MAX_VOLUME
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.specification.binary import MAX_BYTE_VALUE
from sampletones_player.specification.registers import SUSTAINED_LEVEL
from sampletones_tools.codec.study.packing.form import NO_BITS, WHOLE_BYTE, PlaneForm
from sampletones_tools.codec.study.packing.registers import (
    NOISE_CONTROL_FORM,
    NOISE_VALUE_FORM,
    PULSE_CONTROL_FORM,
    register_forms,
)
from sampletones_tools.codec.study.packing.symbols import (
    pack_plane,
    symbol_boundaries,
    unpack_plane,
)

NO_BOUNDARIES: Final[FrozenSet[int]] = frozenset()
QUIET: Final[int] = SUSTAINED_LEVEL
LOUD: Final[int] = SUSTAINED_LEVEL | MAX_VOLUME
LONG_REST: Final[int] = 200


def _noise_control(*volumes: int) -> bytes:
    return bytes(SUSTAINED_LEVEL | volume for volume in volumes)


class TestHowAPlanesByteDivides:
    def test_a_pulse_control_byte_counts_in_the_bits_the_hardware_fixes(self) -> None:
        assert PULSE_CONTROL_FORM.count_mask == SUSTAINED_LEVEL
        assert PULSE_CONTROL_FORM.repeats == 4

    def test_a_noise_control_byte_counts_in_its_whole_top_nibble(self) -> None:
        assert NOISE_CONTROL_FORM.repeats == MAX_VOLUME + 1

    def test_a_noise_period_byte_counts_under_its_mode_bit(self) -> None:
        assert NOISE_VALUE_FORM.repeats == 8

    def test_a_plane_spending_its_whole_byte_counts_nothing(self) -> None:
        assert not WHOLE_BYTE.counts
        assert WHOLE_BYTE.repeats == 1

    def test_the_song_block_names_a_form_for_every_plane(self) -> None:
        assert len(register_forms()) == len(PlaneOrder.names())

    def test_the_value_a_symbol_plays_carries_the_bits_the_register_fixes(self) -> None:
        symbol = NOISE_CONTROL_FORM.symbol(LOUD, repeats=NOISE_CONTROL_FORM.repeats)

        assert NOISE_CONTROL_FORM.value(symbol) == LOUD
        assert NOISE_CONTROL_FORM.repeated(symbol) == NOISE_CONTROL_FORM.repeats

    def test_a_control_plane_is_seeded_to_a_sustained_silence(self) -> None:
        assert PULSE_CONTROL_FORM.seeded == SUSTAINED_LEVEL
        assert NOISE_CONTROL_FORM.seeded == SUSTAINED_LEVEL

    def test_a_plane_spending_its_whole_byte_is_seeded_to_nothing(self) -> None:
        assert WHOLE_BYTE.seeded == NO_BITS

    def test_a_channel_standing_by_leaves_its_control_plane_idle(self) -> None:
        assert PULSE_CONTROL_FORM.idles(_noise_control(*([0] * 8)))

    def test_a_channel_that_sounds_leaves_its_control_plane_standing(self) -> None:
        assert not PULSE_CONTROL_FORM.idles(_noise_control(0, 0, MAX_VOLUME, 0))

    def test_a_form_whose_count_bits_meet_its_value_is_refused(self) -> None:
        with pytest.raises(ValueError):
            PlaneForm(value_mask=0x0F, value_or=0x01)

    def test_a_form_whose_count_bits_lie_apart_is_refused(self) -> None:
        with pytest.raises(ValueError):
            PlaneForm(value_mask=0x7E, value_or=NO_BITS)

    def test_a_value_carrying_other_fixed_bits_is_refused(self) -> None:
        with pytest.raises(ValueError):
            NOISE_CONTROL_FORM.symbol(MAX_VOLUME, repeats=1)

    def test_a_count_past_what_one_symbol_holds_is_refused(self) -> None:
        with pytest.raises(ValueError):
            PULSE_CONTROL_FORM.symbol(QUIET, repeats=PULSE_CONTROL_FORM.repeats + 1)


class TestWhatAPackedPlanePlays:
    def test_the_ticks_come_back_as_they_were_written(self) -> None:
        plane = _noise_control(0, 0, 0, 5, 5, 1, 1, 1, 1, 1, 1, 0)

        packed = pack_plane(plane, NOISE_CONTROL_FORM, boundaries=NO_BOUNDARIES)

        assert unpack_plane(packed, NOISE_CONTROL_FORM) == plane

    def test_a_run_of_one_value_costs_one_symbol(self) -> None:
        plane = _noise_control(*([MAX_VOLUME] * NOISE_CONTROL_FORM.repeats))

        assert len(pack_plane(plane, NOISE_CONTROL_FORM, boundaries=NO_BOUNDARIES)) == 1

    def test_a_run_past_what_one_symbol_counts_takes_as_many_as_it_needs(self) -> None:
        ticks = NOISE_CONTROL_FORM.repeats * 3 + 1
        plane = _noise_control(*([MAX_VOLUME] * ticks))

        packed = pack_plane(plane, NOISE_CONTROL_FORM, boundaries=NO_BOUNDARIES)

        assert len(packed) == 4
        assert unpack_plane(packed, NOISE_CONTROL_FORM) == plane

    def test_a_long_rest_falls_to_a_fraction_of_its_ticks(self) -> None:
        plane = _noise_control(*([0] * LONG_REST))

        packed = pack_plane(plane, NOISE_CONTROL_FORM, boundaries=NO_BOUNDARIES)

        assert len(packed) == ceil(LONG_REST / NOISE_CONTROL_FORM.repeats)

    def test_a_plane_spending_its_whole_byte_packs_to_itself(self) -> None:
        plane = bytes(range(64)) * 2

        assert pack_plane(plane, WHOLE_BYTE, boundaries=NO_BOUNDARIES) == plane

    def test_every_byte_a_symbol_may_take_plays_back(self) -> None:
        symbols = bytes(range(MAX_BYTE_VALUE + 1))

        played = unpack_plane(symbols, NOISE_VALUE_FORM)

        assert len(played) == sum(NOISE_VALUE_FORM.repeated(symbol) for symbol in symbols)
        assert set(played) <= {NOISE_VALUE_FORM.value(symbol) for symbol in symbols}

    def test_a_plane_of_no_ticks_packs_to_no_symbols(self) -> None:
        assert pack_plane(b"", NOISE_CONTROL_FORM, boundaries=NO_BOUNDARIES) == b""


class TestWhereATokenStartsOnAPackedPlane:
    def test_a_boundary_begins_a_symbol_of_its_own(self) -> None:
        plane = _noise_control(*([MAX_VOLUME] * 8))
        boundaries: FrozenSet[int] = frozenset({3})

        packed = pack_plane(plane, NOISE_CONTROL_FORM, boundaries=boundaries)

        assert unpack_plane(packed, NOISE_CONTROL_FORM) == plane
        assert NOISE_CONTROL_FORM.repeated(packed[0]) == 3

    def test_the_boundary_reaches_the_symbol_the_tick_begins(self) -> None:
        plane = _noise_control(*([MAX_VOLUME] * 8))
        boundaries: FrozenSet[int] = frozenset({3})

        assert symbol_boundaries(plane, NOISE_CONTROL_FORM, boundaries=boundaries) == frozenset({1})

    def test_a_plane_spending_its_whole_byte_keeps_its_boundaries(self) -> None:
        plane = bytes(range(16))
        boundaries: FrozenSet[int] = frozenset({4, 9})

        assert symbol_boundaries(plane, WHOLE_BYTE, boundaries=boundaries) == boundaries

    def test_several_boundaries_each_begin_a_symbol(self) -> None:
        plane = _noise_control(*([0] * 40))
        boundaries: FrozenSet[int] = frozenset({5, 17, 33})

        packed = pack_plane(plane, NOISE_CONTROL_FORM, boundaries=boundaries)
        starts = symbol_boundaries(plane, NOISE_CONTROL_FORM, boundaries=boundaries)

        assert unpack_plane(packed, NOISE_CONTROL_FORM) == plane
        assert len(starts) == len(boundaries)
        assert _ticks_before(packed, starts) == {5, 17, 33}


def _ticks_before(packed: bytes, starts: FrozenSet[int]) -> FrozenSet[int]:
    """The tick each named symbol begins on, read by playing the symbols before it."""
    reached: Tuple[int, ...] = tuple(
        sum(NOISE_CONTROL_FORM.repeated(symbol) for symbol in packed[:start]) for start in sorted(starts)
    )
    return frozenset(reached)
