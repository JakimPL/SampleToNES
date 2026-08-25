from dataclasses import dataclass
from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters.naming import instrument_slice_name
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

BASE_NAME: Final[str] = "Kick"


class TestInstrumentSliceName(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class NameCase(BaseRegularTestCase):
        channel: ChannelName
        expected: str

    test_cases = (
        NameCase(
            channel=ChannelName.PULSE1,
            expected="Kick (pulse1)",
            label=ChannelName.PULSE1.value,
        ),
        NameCase(
            channel=ChannelName.PULSE2,
            expected="Kick (pulse2)",
            label=ChannelName.PULSE2.value,
        ),
        NameCase(
            channel=ChannelName.TRIANGLE,
            expected="Kick (triangle)",
            label=ChannelName.TRIANGLE.value,
        ),
        NameCase(
            channel=ChannelName.NOISE,
            expected="Kick (noise)",
            label=ChannelName.NOISE.value,
        ),
    )

    @pytest.mark.parametrize("case", test_cases, ids=lambda case: case.label)
    def test_the_generator_follows_the_base_name_in_parentheses(
        self,
        case: NameCase,
    ) -> None:
        assert instrument_slice_name(BASE_NAME, case.channel) == case.expected

    def test_every_generator_gets_a_distinct_name(self) -> None:
        names = {instrument_slice_name(BASE_NAME, channel) for channel in ChannelName.items()}
        assert len(names) == len(ChannelName.items())

    def test_the_base_name_is_carried_verbatim(self) -> None:
        assert instrument_slice_name("Lead 2 (alt)", ChannelName.PULSE1).startswith("Lead 2 (alt) ")
