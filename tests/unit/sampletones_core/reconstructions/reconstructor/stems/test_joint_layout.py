from typing import Dict, Final, List

import pytest

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName, HierarchyMode, bending_channels
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import (
    Slot,
    StemLayout,
    separate_layouts,
)
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings
from tests.suite.base import BaseTestSuite

PULSE: Final[GeneratorClassName] = GeneratorClassName.PULSE_GENERATOR
TRIANGLE: Final[GeneratorClassName] = GeneratorClassName.TRIANGLE_GENERATOR
NOISE: Final[GeneratorClassName] = GeneratorClassName.NOISE_GENERATOR
LOUDER_DRIVE: Final[float] = 2.0
SOFTER_DRIVE: Final[float] = 0.5


def _stems(entries: Dict[int, List[ChannelName]], channel_cap: int) -> StemsConfig:
    return StemsConfig(
        entries=[
            StemEntry(
                id=stem_id,
                settings=StemSettings(channels=channels, bends=bending_channels(channels), channel_cap=channel_cap),
            )
            for stem_id, channels in entries.items()
        ],
        hierarchy=StemsHierarchy(levels=[list(entries)], mode=HierarchyMode.ROUND_ROBIN),
    )


def _driven_apart() -> StemEntry:
    return StemEntry(
        id=0,
        settings=StemSettings(
            channels=[ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE],
            bends=[],
            drives={
                ChannelName.PULSE1: LOUDER_DRIVE,
                ChannelName.PULSE2: SOFTER_DRIVE,
                ChannelName.TRIANGLE: UNIT_DRIVE,
            },
            channel_cap=3,
        ),
    )


class TestStemLayout(BaseTestSuite):
    def test_a_layout_holds_the_stem_s_channels_in_channel_order_with_their_kinds(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        stems = _stems({0: [ChannelName.TRIANGLE, ChannelName.PULSE2, ChannelName.PULSE1]}, channel_cap=2)

        (layout,) = separate_layouts(stems, all_channels)

        assert [slot.channel_name for slot in layout.slots] == [
            ChannelName.PULSE1,
            ChannelName.PULSE2,
            ChannelName.TRIANGLE,
        ]
        assert layout.kinds == {PULSE, TRIANGLE}
        assert len(layout.of_kind(PULSE)) == 2
        assert layout.cap == 2

    def test_a_kind_s_places_follow_the_channel_order(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        (layout,) = separate_layouts(_stems({0: ChannelName.items()}, channel_cap=4), all_channels)

        assert layout.places_of(PULSE) == (0, 1)
        assert layout.places_of(TRIANGLE) == (2,)
        assert layout.places_of(NOISE) == (3,)

    def test_a_layout_names_only_channels_the_run_plays(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.NOISE]}, channel_cap=2)
        played = {name: all_channels[name] for name in (ChannelName.PULSE1,)}

        layout = StemLayout.of(stems.entries[0], played)

        assert [slot.channel_name for slot in layout.slots] == [ChannelName.PULSE1]

    def test_a_layout_of_one_channel_holds_one_place(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        (layout,) = separate_layouts(_stems({0: [ChannelName.PULSE1]}, channel_cap=1), all_channels)

        assert layout.places_of(PULSE) == (0,)
        assert layout.interchangeable_pulses == ()

    def test_two_stems_allowing_one_channel_are_refused(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE1]}, channel_cap=1)

        with pytest.raises(ValueError, match="one stem"):
            separate_layouts(stems, all_channels)

    def test_stems_on_separate_channels_each_hold_their_own(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE2]}, channel_cap=1)

        first, second = separate_layouts(stems, all_channels)

        assert [slot.channel_name for slot in first.slots] == [ChannelName.PULSE1, ChannelName.TRIANGLE]
        assert [slot.channel_name for slot in second.slots] == [ChannelName.PULSE2]

    def test_pulses_driven_alike_are_interchangeable(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]}, channel_cap=3)

        (layout,) = separate_layouts(stems, all_channels)

        assert layout.interchangeable_pulses == (0, 1)

    def test_pulses_driven_apart_or_alone_are_not_interchangeable(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        alone = _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE]}, channel_cap=2).entries[0]

        assert StemLayout.of(_driven_apart(), all_channels).interchangeable_pulses == ()
        assert StemLayout.of(alone, all_channels).interchangeable_pulses == ()


class TestAKindsGain(BaseTestSuite):
    """A channel at drive ``d`` reads a row at ``1 / d²`` of its power, and a kind's channels add in power."""

    def test_a_kind_s_gain_adds_its_channels_shares_of_a_row_s_power(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        layout = StemLayout.of(_driven_apart(), all_channels)

        assert layout.gain(PULSE) == pytest.approx(1.0 / LOUDER_DRIVE**2 + 1.0 / SOFTER_DRIVE**2)
        assert layout.gain(TRIANGLE) == 1.0

    def test_a_kind_the_stem_lacks_sounds_nothing(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        assert StemLayout.of(_driven_apart(), all_channels).gain(NOISE) == 0.0


class TestASlotsLevels(BaseTestSuite):
    @pytest.mark.parametrize(
        "channel_name, kind", [(ChannelName.PULSE1, PULSE), (ChannelName.NOISE, NOISE)], ids=["pulse", "noise"]
    )
    def test_a_pulse_and_the_noise_play_their_notes_at_many_levels(
        self, channel_name: ChannelName, kind: GeneratorClassName
    ) -> None:
        assert Slot(channel_name=channel_name, kind=kind, drive=UNIT_DRIVE).plays_levels

    def test_the_triangle_plays_one_level(self) -> None:
        assert not Slot(channel_name=ChannelName.TRIANGLE, kind=TRIANGLE, drive=UNIT_DRIVE).plays_levels


class TestThePulseOrders(BaseTestSuite):
    """A combination of pulses driven alike sounds the same in either order, so it may be read in both."""

    def test_pulses_driven_alike_stand_in_both_orders_their_own_first(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        (layout,) = separate_layouts(
            _stems({0: [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]}, channel_cap=3), all_channels
        )

        assert layout.pulse_orders(["lead", "harmony", "bass"]) == [
            ("lead", "harmony", "bass"),
            ("harmony", "lead", "bass"),
        ]

    def test_pulses_driven_apart_or_alone_keep_their_own_order(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        alone = StemLayout.of(
            _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE]}, channel_cap=2).entries[0], all_channels
        )

        assert StemLayout.of(_driven_apart(), all_channels).pulse_orders(["lead", "harmony", "bass"]) == [
            ("lead", "harmony", "bass")
        ]
        assert alone.pulse_orders(["lead", "bass"]) == [("lead", "bass")]
