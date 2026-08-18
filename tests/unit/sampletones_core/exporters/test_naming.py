from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters.naming import instrument_slice_name
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

BASE_NAME: Final[str] = "Kick"


class TestInstrumentSliceName(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class NameCase(BaseRegularTestCase):
        generator: GeneratorName
        expected: str

    test_cases = (
        NameCase(
            generator=GeneratorName.PULSE1,
            expected="Kick (pulse1)",
            label=GeneratorName.PULSE1.value,
        ),
        NameCase(
            generator=GeneratorName.PULSE2,
            expected="Kick (pulse2)",
            label=GeneratorName.PULSE2.value,
        ),
        NameCase(
            generator=GeneratorName.TRIANGLE,
            expected="Kick (triangle)",
            label=GeneratorName.TRIANGLE.value,
        ),
        NameCase(
            generator=GeneratorName.NOISE,
            expected="Kick (noise)",
            label=GeneratorName.NOISE.value,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_generator_follows_the_base_name_in_parentheses(
        self,
        case: NameCase,
    ) -> None:
        assert instrument_slice_name(BASE_NAME, case.generator) == case.expected

    def test_every_generator_gets_a_distinct_name(self) -> None:
        names = {instrument_slice_name(BASE_NAME, generator) for generator in GeneratorName.items()}
        assert len(names) == len(GeneratorName.items())

    def test_the_base_name_is_carried_verbatim(self) -> None:
        assert instrument_slice_name("Lead 2 (alt)", GeneratorName.PULSE1).startswith("Lead 2 (alt) ")
