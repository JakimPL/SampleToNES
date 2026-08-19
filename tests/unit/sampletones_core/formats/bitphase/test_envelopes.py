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

from .conftest import build_features


@dataclass
class PulseWidthCase:
    channel: ChannelName
    duty_cycle: int
    pulse_width: int


PULSE_WIDTH_CASES: List[PulseWidthCase] = [
    PulseWidthCase(channel=ChannelName.PULSE1, duty_cycle=2, pulse_width=2),
    PulseWidthCase(channel=ChannelName.PULSE2, duty_cycle=3, pulse_width=3),
    PulseWidthCase(channel=ChannelName.TRIANGLE, duty_cycle=3, pulse_width=FLAT_PULSE_WIDTH),
    PulseWidthCase(channel=ChannelName.NOISE, duty_cycle=0, pulse_width=NOISE_MODE_LONG),
    PulseWidthCase(channel=ChannelName.NOISE, duty_cycle=1, pulse_width=NOISE_MODE_SHORT),
]

VOLUME_ENVELOPE: Final[List[int]] = [15, 12, 8, 4, 0]
PITCH_CONTOUR: Final[List[int]] = [0, 2, 4, 5, 7]


class TestRowsCarryTheEnvelopes:
    def test_each_volume_item_becomes_one_row(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=False,
        )
        assert [row.volume_or_rate for row in envelopes.rows] == VOLUME_ENVELOPE

    def test_the_contour_becomes_the_table(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=False,
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
            loop=False,
        )
        assert envelopes.rows[0].pulse_width == case.pulse_width

    def test_a_channel_without_a_duty_envelope_plays_one_waveform(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.TRIANGLE,
            loop=False,
        )
        assert {row.pulse_width for row in envelopes.rows} == {FLAT_PULSE_WIDTH}

    def test_a_noise_contour_takes_the_offsets_that_move_its_period(self) -> None:
        steps = [0, 1, -1, 5]
        envelopes = features_to_envelopes(
            build_features([15] * len(steps), arpeggio=steps),
            ChannelName.NOISE,
            loop=False,
        )
        assert list(envelopes.table_rows) == [(-step) % NUM_PERIODS for step in steps]


class TestTheDimensionsStayInStep:
    """Instrument rows and table rows advance on their own per-tick counters, so a
    length they share is what keeps the volume envelope aligned with the pitch contour.
    """

    @pytest.mark.parametrize("loop", [True, False], ids=["looping", "one_shot"])
    def test_the_rows_and_the_table_share_a_length(self, loop: bool) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR[:3]),
            ChannelName.PULSE1,
            loop=loop,
        )
        assert len(envelopes.rows) == len(envelopes.table_rows)

    def test_a_looping_slice_takes_the_shortest_dimension(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR[:2]),
            ChannelName.PULSE1,
            loop=True,
        )
        assert len(envelopes.rows) == 2

    def test_a_one_shot_holds_the_shorter_dimension_to_the_end(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR[:2]),
            ChannelName.PULSE1,
            loop=False,
        )
        assert list(envelopes.table_rows) == [0, 2, 2, 2, 2]

    def test_a_slice_without_a_contour_holds_its_note(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=[]),
            ChannelName.PULSE1,
            loop=False,
        )
        assert list(envelopes.table_rows) == [NO_TABLE_OFFSET] * len(VOLUME_ENVELOPE)


class TestTheLoopPoint:
    def test_a_looping_slice_returns_to_its_first_row(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.PULSE1,
            loop=True,
        )
        assert envelopes.loop == LOOP_FROM_START

    def test_a_one_shot_rests_on_its_last_row(self) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.PULSE1,
            loop=False,
        )
        assert envelopes.loop == len(envelopes.rows) - 1

    def test_a_one_shot_rests_in_silence(self) -> None:
        """Playback always returns to the loop row, so a slice that has played through
        rests on the note-off item its volume envelope ends with.
        """
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE),
            ChannelName.PULSE1,
            loop=False,
        )
        assert envelopes.rows[envelopes.loop].volume_or_rate == SILENT_VOLUME

    @pytest.mark.parametrize("loop", [True, False], ids=["looping", "one_shot"])
    def test_the_loop_row_exists_in_both_lists(self, loop: bool) -> None:
        envelopes = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=loop,
        )
        assert envelopes.loop < len(envelopes.rows)
        assert envelopes.loop < len(envelopes.table_rows)


class TestASliceThatLeavesItsVolumeToTheChannel:
    """An instrument with no volume envelope sounds at the level its channel carries, so
    every frame it describes reaches Bitphase as a full-level row.
    """

    def test_it_holds_a_full_row_per_frame(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=False,
        )
        assert [row.volume_or_rate for row in envelopes.rows] == [MAX_VOLUME_OR_RATE] * len(PITCH_CONTOUR)

    def test_its_contour_still_moves_the_note(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=False,
        )
        assert list(envelopes.table_rows) == PITCH_CONTOUR

    def test_its_duty_envelope_still_reaches_the_rows(self) -> None:
        duty_cycles = [0, 1, 2, 3]
        envelopes = features_to_envelopes(
            build_features([], duty_cycle=duty_cycles),
            ChannelName.PULSE1,
            loop=False,
        )
        assert [row.pulse_width for row in envelopes.rows] == duty_cycles

    def test_a_one_shot_rests_at_the_level_the_channel_holds(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=False,
        )
        assert envelopes.rows[envelopes.loop].volume_or_rate == MAX_VOLUME_OR_RATE

    def test_a_looping_slice_takes_the_length_its_contour_states(self) -> None:
        envelopes = features_to_envelopes(
            build_features([], arpeggio=PITCH_CONTOUR),
            ChannelName.PULSE1,
            loop=True,
        )
        assert len(envelopes.rows) == len(PITCH_CONTOUR)
        assert envelopes.loop == LOOP_FROM_START


class TestAnEmptySlice:
    """An instrument holds at least one row, so a slice with no volume envelope still
    reaches Bitphase as a playable silent instrument.
    """

    @pytest.fixture(name="envelopes")
    def envelopes_fixture(self) -> ChannelEnvelopes:
        return features_to_envelopes(build_features([]), ChannelName.PULSE1, loop=False)

    def test_it_holds_one_silent_row(self, envelopes: ChannelEnvelopes) -> None:
        assert [row.volume_or_rate for row in envelopes.rows] == [SILENT_VOLUME]

    def test_its_table_holds_one_flat_offset(self, envelopes: ChannelEnvelopes) -> None:
        assert envelopes.table_rows == (NO_TABLE_OFFSET,)

    def test_it_loops_on_that_row(self, envelopes: ChannelEnvelopes) -> None:
        assert envelopes.loop == LOOP_FROM_START
