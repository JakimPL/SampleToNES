from dataclasses import dataclass
from typing import Dict, Final, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName
from sampletones_core.generators import GeneratorUnion, get_generators_by_channels
from sampletones_core.reconstructions.reconstructor.stems.assignment.columns import column_groups
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

LOUD_DRIVE: Final[float] = 2.0


@pytest.fixture(name="generators", scope="module")
def generators_fixture(config: Config) -> Dict[ChannelName, GeneratorUnion]:
    return get_generators_by_channels(config, ChannelName.items())


def _remaining(
    generators: Dict[ChannelName, GeneratorUnion],
    channel_names: List[ChannelName],
) -> Dict[ChannelName, GeneratorUnion]:
    return {channel_name: generators[channel_name] for channel_name in channel_names}


class TestColumnGroups:
    """One column answers the channels of a kind a stem drives alike, and each drive stands apart."""

    def test_channels_of_one_kind_driven_alike_form_one_group(
        self,
        generators: Dict[ChannelName, GeneratorUnion],
    ) -> None:
        remaining = _remaining(generators, [ChannelName.PULSE1, ChannelName.PULSE2])
        drives = {ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: UNIT_DRIVE}

        groups = column_groups(remaining, drives)

        assert [(group.generator.name, group.drive) for group in groups] == [(ChannelName.PULSE1, UNIT_DRIVE)]

    def test_the_lowest_channel_left_stands_for_its_group(
        self,
        generators: Dict[ChannelName, GeneratorUnion],
    ) -> None:
        remaining = _remaining(generators, [ChannelName.PULSE2])

        groups = column_groups(remaining, {ChannelName.PULSE2: UNIT_DRIVE})

        assert [group.generator.name for group in groups] == [ChannelName.PULSE2]

    def test_channels_of_one_kind_driven_apart_form_a_group_each(
        self,
        generators: Dict[ChannelName, GeneratorUnion],
    ) -> None:
        remaining = _remaining(generators, [ChannelName.PULSE1, ChannelName.PULSE2])
        drives = {ChannelName.PULSE1: UNIT_DRIVE, ChannelName.PULSE2: LOUD_DRIVE}

        groups = column_groups(remaining, drives)

        assert [(group.generator.name, group.drive) for group in groups] == [
            (ChannelName.PULSE1, UNIT_DRIVE),
            (ChannelName.PULSE2, LOUD_DRIVE),
        ]

    def test_the_groups_stand_in_channel_order(
        self,
        generators: Dict[ChannelName, GeneratorUnion],
    ) -> None:
        remaining = _remaining(generators, [ChannelName.NOISE, ChannelName.PULSE1, ChannelName.TRIANGLE])

        groups = column_groups(remaining, dict.fromkeys(remaining, UNIT_DRIVE))

        assert [group.generator.name for group in groups] == [
            ChannelName.PULSE1,
            ChannelName.TRIANGLE,
            ChannelName.NOISE,
        ]

    def test_no_channel_left_offers_no_group(self) -> None:
        assert column_groups({}, {}) == []


class TestColumnGroupsAgreeWithTheJointLayout(BaseTestSuite):
    """The picks assignment scores a column for each group the joint assignment's layout holds: one rule groups both."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        channels: List[ChannelName]
        drives: Dict[ChannelName, float]

    test_cases = (
        TestCase(label="every_channel_alike", channels=ChannelName.items(), drives={}),
        TestCase(label="first_pulse_louder", channels=ChannelName.items(), drives={ChannelName.PULSE1: LOUD_DRIVE}),
        TestCase(label="second_pulse_louder", channels=ChannelName.items(), drives={ChannelName.PULSE2: LOUD_DRIVE}),
        TestCase(
            label="pulses_alike_away_from_unit",
            channels=[ChannelName.PULSE1, ChannelName.PULSE2],
            drives={ChannelName.PULSE1: LOUD_DRIVE, ChannelName.PULSE2: LOUD_DRIVE},
        ),
        TestCase(
            label="second_pulse_and_noise",
            channels=[ChannelName.PULSE2, ChannelName.NOISE],
            drives={ChannelName.NOISE: LOUD_DRIVE},
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_each_column_stands_for_the_lowest_channel_of_a_layout_group_at_its_drive(
        self, test_case: TestCase, generators: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        drives = {channel_name: test_case.drives.get(channel_name, UNIT_DRIVE) for channel_name in test_case.channels}
        settings = StemSettings(
            channels=test_case.channels, bends=[], drives=drives, channel_cap=len(test_case.channels)
        )
        layout = StemLayout.of(StemEntry(id=0, settings=settings), generators)

        groups = column_groups(_remaining(generators, test_case.channels), drives)

        assert [(group.generator.name, group.drive) for group in groups] == [
            (layout.slots[group.places[0]].channel_name, group.drive) for group in layout.groups
        ]
