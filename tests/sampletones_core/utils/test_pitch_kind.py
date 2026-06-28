from dataclasses import dataclass

import pytest

from sampletones_core.constants.general import MAX_PERIOD, MAX_PITCH, MIN_PITCH
from sampletones_core.utils.pitch_kind import PERIOD, PITCH, PitchValueKind


@dataclass(frozen=True)
class ClampCase:
    kind: PitchValueKind
    value: int
    expected: int


CLAMP_CASES = [
    ClampCase(PITCH, MIN_PITCH - 10, MIN_PITCH),
    ClampCase(PITCH, MAX_PITCH + 10, MAX_PITCH),
    ClampCase(PITCH, 60, 60),
    ClampCase(PERIOD, -5, 0),
    ClampCase(PERIOD, MAX_PERIOD + 5, MAX_PERIOD),
    ClampCase(PERIOD, 4, 4),
]


@pytest.mark.parametrize("case", CLAMP_CASES)
def test_clamp_restricts_to_range(case: ClampCase) -> None:
    assert case.kind.clamp(case.value) == case.expected


class TestPitchFromText:
    def test_integer_text_is_clamped_into_range(self) -> None:
        assert PITCH.from_text("9999", fallback=50) == MAX_PITCH

    def test_note_name_resolves_to_pitch(self) -> None:
        assert PITCH.from_text("C-3", fallback=50) == PITCH.sanitized_name_to_value["C-3"]

    def test_unparseable_text_falls_back(self) -> None:
        assert PITCH.from_text("not a note", fallback=55) == 55

    def test_round_trip_through_name(self) -> None:
        assert PITCH.from_text(PITCH.to_name(72), fallback=0) == 72


class TestPeriodFromText:
    def test_integer_text_is_clamped_into_range(self) -> None:
        assert PERIOD.from_text("9999", fallback=0) == MAX_PERIOD

    def test_hex_name_resolves_to_period(self) -> None:
        assert PERIOD.from_text("A-#", fallback=0) == 10

    def test_unparseable_text_falls_back(self) -> None:
        assert PERIOD.from_text("not a period", fallback=3) == 3

    def test_round_trip_through_name(self) -> None:
        assert PERIOD.from_text(PERIOD.to_name(11), fallback=0) == 11
