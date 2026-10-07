from dataclasses import dataclass

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH, MIN_PLAYED_PITCH
from sampletones_core.utils.pitch_kind import (
    PERIOD_VALUE_KIND,
    PITCH_VALUE_KIND,
    PLAYED_PITCH_VALUE_KIND,
    PitchValueKind,
    note_value_kind,
)


@dataclass(frozen=True)
class ClampCase:
    kind: PitchValueKind
    value: int
    expected: int


CLAMP_CASES = [
    ClampCase(PITCH_VALUE_KIND, MIN_PITCH - 10, MIN_PITCH),
    ClampCase(PITCH_VALUE_KIND, MAX_PITCH + 10, MAX_PITCH),
    ClampCase(PITCH_VALUE_KIND, 60, 60),
    ClampCase(PLAYED_PITCH_VALUE_KIND, MIN_PLAYED_PITCH - 10, MIN_PLAYED_PITCH),
    ClampCase(PLAYED_PITCH_VALUE_KIND, MAX_PITCH + 10, MAX_PITCH),
    ClampCase(PLAYED_PITCH_VALUE_KIND, MIN_PLAYED_PITCH, MIN_PLAYED_PITCH),
    ClampCase(PERIOD_VALUE_KIND, -5, 0),
    ClampCase(PERIOD_VALUE_KIND, MAX_PERIOD + 5, MAX_PERIOD),
    ClampCase(PERIOD_VALUE_KIND, 4, 4),
]


@pytest.mark.parametrize("case", CLAMP_CASES)
def test_clamp_restricts_to_range(case: ClampCase) -> None:
    assert case.kind.clamp(case.value) == case.expected


class TestPitchFromText:
    def test_integer_text_is_clamped_into_range(self) -> None:
        assert PITCH_VALUE_KIND.from_text("9999", fallback=50) == MAX_PITCH

    def test_note_name_resolves_to_pitch(self) -> None:
        assert PITCH_VALUE_KIND.from_text("C-3", fallback=50) == PITCH_VALUE_KIND.sanitized_name_to_value["C-3"]

    def test_unparseable_text_falls_back(self) -> None:
        assert PITCH_VALUE_KIND.from_text("not a note", fallback=55) == 55

    def test_round_trip_through_name(self) -> None:
        assert PITCH_VALUE_KIND.from_text(PITCH_VALUE_KIND.to_name(72), fallback=0) == 72


class TestPeriodFromText:
    def test_integer_text_is_clamped_into_range(self) -> None:
        assert PERIOD_VALUE_KIND.from_text("9999", fallback=0) == MAX_PERIOD

    def test_hex_name_resolves_to_period(self) -> None:
        assert PERIOD_VALUE_KIND.from_text("A-#", fallback=0) == 10

    def test_unparseable_text_falls_back(self) -> None:
        assert PERIOD_VALUE_KIND.from_text("not a period", fallback=3) == 3

    def test_round_trip_through_name(self) -> None:
        assert PERIOD_VALUE_KIND.from_text(PERIOD_VALUE_KIND.to_name(11), fallback=0) == 11


class TestNoteValueKind:
    """A row's note is held to the notes a tonal channel plays, from C-0 up, and to the periods on noise."""

    @pytest.mark.parametrize("channel_name", [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE])
    def test_a_tonal_channel_plays_from_the_lowest_note(self, channel_name: ChannelName) -> None:
        assert note_value_kind(channel_name) is PLAYED_PITCH_VALUE_KIND

    def test_the_noise_channel_names_its_periods(self) -> None:
        assert note_value_kind(ChannelName.NOISE) is PERIOD_VALUE_KIND

    def test_the_lowest_note_has_a_name_the_played_kind_reads(self) -> None:
        lowest = PLAYED_PITCH_VALUE_KIND.to_name(MIN_PLAYED_PITCH)

        assert (
            PLAYED_PITCH_VALUE_KIND.sanitized_name_to_value[PLAYED_PITCH_VALUE_KIND.sanitize(lowest)]
            == MIN_PLAYED_PITCH
        )
        assert PLAYED_PITCH_VALUE_KIND.sanitize(lowest) not in PITCH_VALUE_KIND.sanitized_name_to_value
