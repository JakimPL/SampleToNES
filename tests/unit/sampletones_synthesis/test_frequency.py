from dataclasses import dataclass
from typing import Any, Final, Tuple

import pytest
from pydantic import TypeAdapter, ValidationError

from sampletones_synthesis.frequency import FrequencySpec, resolve_frequency

FREQUENCY_SPEC_ADAPTER: Final[TypeAdapter[Any]] = TypeAdapter(FrequencySpec)


@dataclass(frozen=True)
class ResolveCase:
    name: str
    value: Any
    expected_hertz: float


@dataclass(frozen=True)
class InvalidSpecCase:
    name: str
    value: Any


RESOLVE_CASES: Final[Tuple[ResolveCase, ...]] = (
    ResolveCase(name="a4_pitch", value=69, expected_hertz=440.0),
    ResolveCase(name="a3_pitch", value=57, expected_hertz=220.0),
    ResolveCase(name="hertz_passthrough", value=432.1, expected_hertz=432.1),
)

INVALID_SPEC_CASES: Final[Tuple[InvalidSpecCase, ...]] = (
    InvalidSpecCase(name="integer_above_pitch_range", value=440),
    InvalidSpecCase(name="integer_below_pitch_range", value=23),
    InvalidSpecCase(name="boolean", value=True),
    InvalidSpecCase(name="numeric_string", value="440"),
    InvalidSpecCase(name="zero_hertz", value=0.0),
    InvalidSpecCase(name="negative_hertz", value=-5.0),
)


class TestFrequencySpec:
    @pytest.mark.parametrize("case", RESOLVE_CASES, ids=lambda case: case.name)
    def test_valid_specification_resolves_to_hertz(self, case: ResolveCase) -> None:
        value = FREQUENCY_SPEC_ADAPTER.validate_python(case.value)
        assert resolve_frequency(value) == pytest.approx(case.expected_hertz)

    def test_pitch_stays_integer_and_hertz_stays_float(self) -> None:
        assert isinstance(FREQUENCY_SPEC_ADAPTER.validate_python(67), int)
        assert isinstance(FREQUENCY_SPEC_ADAPTER.validate_python(440.0), float)

    @pytest.mark.parametrize("case", INVALID_SPEC_CASES, ids=lambda case: case.name)
    def test_invalid_specification_is_rejected(self, case: InvalidSpecCase) -> None:
        with pytest.raises(ValidationError):
            FREQUENCY_SPEC_ADAPTER.validate_python(case.value)
