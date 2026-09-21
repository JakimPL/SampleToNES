from typing import Final, List, Optional, Sequence

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import HI_PITCH_FACTOR
from sampletones_core.formats.bitphase.envelopes import features_to_envelopes
from sampletones_core.formats.bitphase.notes import pitch_to_note_index
from sampletones_core.formats.bitphase.preset import instrument_to_preset
from sampletones_core.formats.bitphase.specification.chip import (
    MAX_TUNING_PERIOD,
    MIN_TUNING_PERIOD,
)
from sampletones_core.formats.bitphase.specification.instruments import (
    MAX_TONE_ADD,
    MIN_TONE_ADD,
    NO_TONE_OFFSET,
)
from sampletones_core.formats.bitphase.specification.macros import NesMacroField
from sampletones_core.formats.bitphase.tuning import DEFAULT_TUNING_TABLE

from .conftest import REFERENCE_PITCH, build_features, build_instrument

VOLUME_ENVELOPE: Final[List[int]] = [15, 12, 8, 4]
BEND_ENVELOPE: Final[List[int]] = [0, -3, -7, -12]
PITCH_CONTOUR: Final[List[int]] = [0, 5, 7, 12]
BASE_INDEX: Final[int] = pitch_to_note_index(REFERENCE_PITCH)
BASE_PERIOD: Final[int] = DEFAULT_TUNING_TABLE[BASE_INDEX]


def offsets(
    channel: ChannelName = ChannelName.PULSE1,
    *,
    arpeggio: Optional[Sequence[int]] = None,
    bend: Optional[Sequence[int]] = None,
    coarse_bend: Optional[Sequence[int]] = None,
) -> List[int]:
    features = build_features(
        VOLUME_ENVELOPE,
        arpeggio=arpeggio,
        bend=bend,
        coarse_bend=coarse_bend,
    )
    macro = features_to_envelopes(features, channel).macros.get(NesMacroField.TONE_ADD)
    return [] if macro is None else list(macro.values)


class TestTheBendReachesTheToneOffset:
    def test_each_step_offsets_the_period_by_that_many(self) -> None:
        assert offsets(bend=BEND_ENVELOPE) == BEND_ENVELOPE

    def test_a_coarse_step_counts_sixteen(self) -> None:
        """The two dimensions state one bend together, at one step and at sixteen apiece."""
        assert offsets(bend=[1, 1], coarse_bend=[0, 2]) == [1, 1 + 2 * HI_PITCH_FACTOR]

    def test_a_slice_sounding_on_its_note_writes_no_offset(self) -> None:
        assert offsets(bend=[0, 0, 0, 0]) == []

    def test_a_slice_without_the_dimension_writes_no_offset(self) -> None:
        assert offsets(arpeggio=PITCH_CONTOUR) == []

    def test_the_triangle_channel_bends_its_period(self) -> None:
        assert offsets(ChannelName.TRIANGLE, bend=BEND_ENVELOPE) == BEND_ENVELOPE

    def test_the_noise_channel_takes_its_period_from_the_note(self) -> None:
        assert offsets(ChannelName.NOISE, bend=BEND_ENVELOPE) == []

    def test_the_bend_circles_from_the_point_it_states(self) -> None:
        written = features_to_envelopes(
            build_features(VOLUME_ENVELOPE, bend=BEND_ENVELOPE),
            ChannelName.PULSE1,
        )
        assert written.macros[NesMacroField.TONE_ADD].loop == len(BEND_ENVELOPE) - 1


class TestTheNoteABendIsMeasuredFrom:
    """The table moves the note before Bitphase resolves its period, and the offset is added
    to that period, so each tick is measured from the note its own contour step reaches.
    """

    def test_a_moved_note_keeps_the_steps_the_slice_states(self) -> None:
        assert offsets(arpeggio=PITCH_CONTOUR, bend=BEND_ENVELOPE) == BEND_ENVELOPE

    def test_a_contour_holding_its_last_step_carries_the_bend_on(self) -> None:
        assert offsets(arpeggio=[0, 12], bend=[-4, -4, -4, -4]) == [-4, -4, -4, -4]


class TestABendThePeriodRangeHolds:
    @pytest.mark.parametrize("steps", [MIN_TONE_ADD, MAX_TONE_ADD], ids=["down", "up"])
    def test_the_period_it_reaches_stays_within_the_timer(self, steps: int) -> None:
        written = offsets(bend=[steps] * len(VOLUME_ENVELOPE))
        assert all(MIN_TUNING_PERIOD <= BASE_PERIOD + offset <= MAX_TUNING_PERIOD for offset in written)

    def test_a_bend_past_the_shortest_period_stops_there(self) -> None:
        assert offsets(bend=[-BASE_PERIOD - 100] * len(VOLUME_ENVELOPE))[0] == MIN_TUNING_PERIOD - BASE_PERIOD

    def test_every_offset_fits_the_field(self) -> None:
        written = offsets(bend=[MAX_TONE_ADD] * len(VOLUME_ENVELOPE))
        assert all(MIN_TONE_ADD <= offset <= MAX_TONE_ADD for offset in written)


class TestAPresetCarriesBothMovements:
    """A preset holds no table, so its tone offset carries the contour and the bend together."""

    def test_its_offsets_add_the_bend_to_the_contour(self) -> None:
        preset = instrument_to_preset(
            build_instrument(
                "Lead",
                build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR, bend=BEND_ENVELOPE),
            ),
        )
        expected = [
            DEFAULT_TUNING_TABLE[BASE_INDEX + semitones] - BASE_PERIOD + steps
            for semitones, steps in zip(PITCH_CONTOUR, BEND_ENVELOPE)
        ]
        assert list(preset.macros[NesMacroField.TONE_ADD].values) == expected

    def test_an_unbent_slice_carries_its_contour_alone(self) -> None:
        preset = instrument_to_preset(
            build_instrument("Pad", build_features(VOLUME_ENVELOPE, arpeggio=PITCH_CONTOUR)),
        )
        expected = [DEFAULT_TUNING_TABLE[BASE_INDEX + semitones] - BASE_PERIOD for semitones in PITCH_CONTOUR]
        assert list(preset.macros[NesMacroField.TONE_ADD].values) == expected

    def test_a_noise_slice_takes_its_period_from_the_note(self) -> None:
        preset = instrument_to_preset(
            build_instrument(
                "Hat",
                build_features(VOLUME_ENVELOPE, bend=BEND_ENVELOPE, initial_pitch=4),
                channel=ChannelName.NOISE,
            ),
        )
        assert set(preset.macros[NesMacroField.TONE_ADD].values) == {NO_TONE_OFFSET}
