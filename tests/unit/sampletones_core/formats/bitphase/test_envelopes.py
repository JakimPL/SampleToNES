from dataclasses import dataclass
from typing import Final, List

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import NUM_PERIODS
from sampletones_core.formats.bitphase.envelopes import (
    ChannelEnvelopes,
    features_to_envelopes,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    FLAT_PULSE_WIDTH,
    LOOP_FROM_START,
    MAX_VOLUME_OR_RATE,
    NO_TABLE_OFFSET,
    NOISE_MODE_LONG,
    NOISE_MODE_SHORT,
    SILENT_VOLUME,
)
from sampletones_core.formats.bitphase.specification.macros import MAX_MACRO_LENGTH, NesMacroField

from .conftest import build_features, looping


@dataclass
class PulseWidthCase:
    channel: ChannelName
    duty_cycle: int
    pulse_width: int


PULSE_WIDTH_CASES: List[PulseWidthCase] = [
    PulseWidthCase(channel=ChannelName.PULSE1, duty_cycle=2, pulse_width=2),
    PulseWidthCase(channel=ChannelName.PULSE2, duty_cycle=3, pulse_width=3),
    PulseWidthCase(channel=ChannelName.NOISE, duty_cycle=0, pulse_width=NOISE_MODE_LONG),
    PulseWidthCase(channel=ChannelName.NOISE, duty_cycle=1, pulse_width=NOISE_MODE_SHORT),
]

VOLUME_ENVELOPE: Final[List[int]] = [15, 12, 8, 4, 0]
PITCH_CONTOUR: Final[List[int]] = [0, 2, 4, 5, 7]


def volume_values(envelopes: ChannelEnvelopes) -> List[int]:
    return list(envelopes.macros[NesMacroField.VOLUME_OR_RATE].values)


def waveform_values(envelopes: ChannelEnvelopes) -> List[int]:
    return list(envelopes.macros[NesMacroField.PULSE_WIDTH].values)


class TestEachDimensionBecomesItsOwnMacro:
    def test_the_volume_envelope_becomes_the_level_a_tick_takes(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
        )
        assert volume_values(envelopes) == VOLUME_ENVELOPE

    def test_the_contour_becomes_the_table(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
        )
        assert list(envelopes.table_rows) == PITCH_CONTOUR

    @pytest.mark.parametrize(
        "case",
        PULSE_WIDTH_CASES,
        ids=lambda case: f"{case.channel}-{case.duty_cycle}",
    )
    def test_the_duty_item_reaches_the_field_its_channel_reads(self, case: PulseWidthCase) -> None:
        envelopes = features_to_envelopes(
            build_features([15], duty_cycle=[case.duty_cycle]),
            case.channel,
        )
        assert waveform_values(envelopes) == [case.pulse_width]

    def test_the_triangle_channel_leaves_its_one_waveform_alone(self) -> None:
        """The triangle plays a single waveform, so the field it would name stays at its default."""
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, duty_cycle=[3] * len(VOLUME_ENVELOPE)),
            ChannelName.TRIANGLE,
        )
        assert set(envelopes.macros) == {NesMacroField.VOLUME_OR_RATE}

    def test_a_channel_without_a_duty_envelope_holds_one_waveform(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.PULSE1,
        )
        assert waveform_values(envelopes) == [FLAT_PULSE_WIDTH]

    def test_a_noise_contour_takes_the_offsets_that_move_its_period(self) -> None:
        steps = [0, 1, -1, 5]
        envelopes = features_to_envelopes(
            build_features([15] * len(steps), arpeggio=steps),
            ChannelName.NOISE,
        )
        assert list(envelopes.table_rows) == [(-step) % NUM_PERIODS for step in steps]


class TestEachDimensionKeepsItsOwnLength:
    """Bitphase advances every field on a counter of its own, so a dimension holding one
    value all through costs that one value however long the others run.
    """

    def test_a_dimension_holds_the_length_it_was_written_at(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR[:2]),
            ChannelName.PULSE1,
        )
        assert len(volume_values(envelopes)) == len(VOLUME_ENVELOPE)
        assert len(envelopes.table_rows) == 2

    def test_a_slice_without_a_contour_holds_one_step(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=[]),
            ChannelName.PULSE1,
        )
        assert list(envelopes.table_rows) == [NO_TABLE_OFFSET]

    def test_the_instrument_runs_as_long_as_its_longest_dimension(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR[:2]),
            ChannelName.PULSE1,
        )
        assert envelopes.ticks == len(VOLUME_ENVELOPE)


class TestThePointADimensionRepeatsFrom:
    def test_a_looping_dimension_states_the_point_it_circles_from(self) -> None:
        envelopes = features_to_envelopes(
            looping(build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR), 0),
            ChannelName.PULSE1,
        )
        assert envelopes.macros[NesMacroField.VOLUME_OR_RATE].loop == LOOP_FROM_START
        assert envelopes.table_loop == LOOP_FROM_START

    def test_a_one_shot_holds_its_final_value(self) -> None:
        """Circling from the last value is what holds it, since playback never halts."""
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
        )
        assert envelopes.macros[NesMacroField.VOLUME_OR_RATE].loop == len(VOLUME_ENVELOPE) - 1
        assert envelopes.table_loop == len(PITCH_CONTOUR) - 1

    def test_a_one_shot_rests_in_silence(self) -> None:
        """A slice that has played through rests on the note-off item its volume ends with."""
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.PULSE1,
        )
        macro = envelopes.macros[NesMacroField.VOLUME_OR_RATE]
        assert macro.values[macro.loop] == SILENT_VOLUME

    @pytest.mark.parametrize("loop", [True, False], ids=["looping", "one_shot"])
    def test_every_point_stands_among_the_values_it_circles(self, loop: bool) -> None:
        envelopes = features_to_envelopes(
            looping(build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR), 0 if loop else None),
            ChannelName.PULSE1,
        )
        assert all(macro.loop < len(macro.values) for macro in envelopes.macros.values())
        assert envelopes.table_loop < len(envelopes.table_rows)


class TestASliceThatLeavesItsVolumeToTheChannel:
    """An instrument with no volume envelope sounds at the level its channel carries, so
    one full level is what it writes.
    """

    def test_it_holds_one_full_level(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
        )
        assert volume_values(envelopes) == [MAX_VOLUME_OR_RATE]

    def test_its_contour_still_moves_the_note(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
        )
        assert list(envelopes.table_rows) == PITCH_CONTOUR

    def test_its_duty_envelope_still_reaches_the_waveform(self) -> None:
        duty_cycles = [0, 1, 2, 3]
        envelopes = features_to_envelopes(
            build_features([], duty_cycle=duty_cycles),
            ChannelName.PULSE1,
        )
        assert waveform_values(envelopes) == duty_cycles


class TestADimensionPastWhatAMacroStores:
    def test_it_keeps_its_opening_values(self) -> None:
        contour = list(range(MAX_MACRO_LENGTH + 8))
        envelopes = features_to_envelopes(
            build_features([MAX_VOLUME_OR_RATE] * (MAX_MACRO_LENGTH + 8), arpeggio=contour),
            ChannelName.PULSE1,
        )
        assert len(volume_values(envelopes)) == MAX_MACRO_LENGTH

    def test_a_volume_ending_in_silence_keeps_that_silence(self) -> None:
        """A shortened volume that dropped its note-off would sound on for as long as the note does."""
        volume = [MAX_VOLUME_OR_RATE] * (MAX_MACRO_LENGTH + 8) + [SILENT_VOLUME]
        envelopes = features_to_envelopes(build_features(volume), ChannelName.PULSE1)
        assert volume_values(envelopes)[-1] == SILENT_VOLUME

    def test_the_table_carries_a_contour_of_any_length(self) -> None:
        contour = list(range(MAX_MACRO_LENGTH + 8))
        envelopes = features_to_envelopes(
            build_features([MAX_VOLUME_OR_RATE], arpeggio=contour),
            ChannelName.PULSE1,
        )
        assert len(envelopes.table_rows) == len(contour)


class TestAnEmptySlice:
    """An instrument holds at least one value, so a slice with no volume envelope still
    reaches Bitphase as a playable silent instrument.
    """

    @pytest.fixture(name="envelopes")
    def envelopes_fixture(self) -> ChannelEnvelopes:
        return features_to_envelopes(build_features([]), ChannelName.PULSE1)

    def test_it_holds_one_silent_level(self, envelopes: ChannelEnvelopes) -> None:
        assert volume_values(envelopes) == [SILENT_VOLUME]

    def test_its_table_holds_one_flat_offset(self, envelopes: ChannelEnvelopes) -> None:
        assert envelopes.table_rows == (NO_TABLE_OFFSET,)

    def test_it_circles_that_value(self, envelopes: ChannelEnvelopes) -> None:
        assert envelopes.macros[NesMacroField.VOLUME_OR_RATE].loop == LOOP_FROM_START
        assert envelopes.table_loop == LOOP_FROM_START
