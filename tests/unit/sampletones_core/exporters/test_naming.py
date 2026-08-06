from dataclasses import dataclass
from typing import Final, List

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.naming import instrument_slice_name

BASE_NAME: Final[str] = "Kick"


@dataclass(frozen=True)
class NameCase:
    generator: GeneratorName
    expected: str


NAME_CASES: Final[List[NameCase]] = [
    NameCase(generator=GeneratorName.PULSE1, expected="Kick (pulse1)"),
    NameCase(generator=GeneratorName.PULSE2, expected="Kick (pulse2)"),
    NameCase(generator=GeneratorName.TRIANGLE, expected="Kick (triangle)"),
    NameCase(generator=GeneratorName.NOISE, expected="Kick (noise)"),
]


class TestInstrumentSliceName:
    @pytest.mark.parametrize("case", NAME_CASES, ids=lambda case: case.generator.value)
    def test_the_generator_follows_the_base_name_in_parentheses(self, case: NameCase) -> None:
        assert instrument_slice_name(BASE_NAME, case.generator) == case.expected

    def test_every_generator_gets_a_distinct_name(self) -> None:
        names = {instrument_slice_name(BASE_NAME, generator) for generator in GeneratorName.items()}
        assert len(names) == len(GeneratorName.items())

    def test_the_base_name_is_carried_verbatim(self) -> None:
        assert instrument_slice_name("Lead 2 (alt)", GeneratorName.PULSE1).startswith("Lead 2 (alt) ")
