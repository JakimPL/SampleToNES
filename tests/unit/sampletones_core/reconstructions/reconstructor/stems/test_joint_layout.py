from typing import Dict, Final, List, Tuple

import pytest

from sampletones_core.constants.algorithm import UNIT_DRIVE
from sampletones_core.constants.enums import ChannelName, GeneratorClassName, HierarchyMode, bending_channels
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import (
    ChannelGroup,
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
        assert layout.shared_groups == ()

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


def _pulses_at(first: float, second: float) -> StemLayout:
    """A stem of both pulses, driven at ``first`` and ``second``, and the triangle at unit drive."""
    slots = (
        Slot(channel_name=ChannelName.PULSE1, kind=PULSE, drive=first),
        Slot(channel_name=ChannelName.PULSE2, kind=PULSE, drive=second),
        Slot(channel_name=ChannelName.TRIANGLE, kind=TRIANGLE, drive=UNIT_DRIVE),
    )
    return StemLayout(stem_id=0, slots=slots, cap=len(slots))


def _described(groups: Tuple[ChannelGroup, ...]) -> List[Tuple[GeneratorClassName, float, Tuple[int, ...]]]:
    return [(group.kind, group.drive, group.places) for group in groups]


class TestTheChannelGroups(BaseTestSuite):
    """A stem's channels fall into groups of one kind at one drive, standing in the order of their lowest channels."""

    def test_channels_of_one_kind_driven_alike_form_one_group(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        (layout,) = separate_layouts(_stems({0: ChannelName.items()}, channel_cap=4), all_channels)

        assert _described(layout.groups) == [
            (PULSE, UNIT_DRIVE, (0, 1)),
            (TRIANGLE, UNIT_DRIVE, (2,)),
            (NOISE, UNIT_DRIVE, (3,)),
        ]
        assert _described(layout.shared_groups) == [(PULSE, UNIT_DRIVE, (0, 1))]

    def test_channels_of_one_kind_driven_apart_form_a_group_each(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        layout = StemLayout.of(_driven_apart(), all_channels)

        assert _described(layout.groups) == [
            (PULSE, LOUDER_DRIVE, (0,)),
            (PULSE, SOFTER_DRIVE, (1,)),
            (TRIANGLE, UNIT_DRIVE, (2,)),
        ]
        assert layout.shared_groups == ()

    def test_channels_driven_alike_away_from_unit_drive_form_one_group(self) -> None:
        layout = _pulses_at(LOUDER_DRIVE, LOUDER_DRIVE)

        assert _described(layout.groups_of(PULSE)) == [(PULSE, LOUDER_DRIVE, (0, 1))]

    def test_a_stem_of_no_channel_holds_no_group(self) -> None:
        assert StemLayout(stem_id=0, slots=(), cap=0).groups == ()

    @pytest.mark.parametrize(
        "first, second", [(LOUDER_DRIVE, SOFTER_DRIVE), (SOFTER_DRIVE, LOUDER_DRIVE)], ids=["louder", "softer"]
    )
    def test_a_kind_fills_the_lowest_channel_of_its_first_group_first(self, first: float, second: float) -> None:
        layout = _pulses_at(first, second)

        assert layout.first_place(PULSE) == 0
        assert layout.first_place(TRIANGLE) == 2


class TestARelativeLevel(BaseTestSuite):
    """Two channels sound a row alike at levels in the ratio of their squared drives."""

    def test_channels_of_one_group_sound_a_row_alike_at_one_level(self) -> None:
        layout = _pulses_at(LOUDER_DRIVE, LOUDER_DRIVE)

        assert layout.relative_level(0, 1) == 1.0
        assert layout.relative_level(1, 0) == 1.0

    @pytest.mark.parametrize("place, other", [(0, 1), (1, 0)], ids=["louder_against_softer", "softer_against_louder"])
    def test_across_groups_a_level_scales_by_the_squared_ratio_of_the_drives(self, place: int, other: int) -> None:
        layout = _pulses_at(LOUDER_DRIVE, SOFTER_DRIVE)
        drives = [LOUDER_DRIVE, SOFTER_DRIVE]

        heard_there = 1.0 / drives[other] ** 2
        heard_here = layout.relative_level(place, other) / drives[place] ** 2
        assert heard_here == pytest.approx(heard_there)


class TestAChannelsGain(BaseTestSuite):
    """A channel at drive ``d`` reads a row at ``1 / d²`` of its power, and a kind's channels add in power.

    A channel's gain counts what every channel of its kind sounds of a row in the row's power on that
    channel, so on either channel it reaches the kind's whole share of the row's library power.
    """

    @pytest.mark.parametrize("place", [0, 1], ids=["louder_pulse", "softer_pulse"])
    def test_on_either_pulse_the_gain_reaches_what_both_pulses_sound(
        self, place: int, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        layout = StemLayout.of(_driven_apart(), all_channels)

        heard_on_the_channel = 1.0 / layout.slots[place].drive ** 2
        assert layout.gain(place) * heard_on_the_channel == pytest.approx(1.0 / LOUDER_DRIVE**2 + 1.0 / SOFTER_DRIVE**2)

    @pytest.mark.parametrize("drive", [UNIT_DRIVE, LOUDER_DRIVE, SOFTER_DRIVE], ids=["unit", "louder", "softer"])
    def test_a_lone_channel_of_its_kind_gains_one_at_any_drive(self, drive: float) -> None:
        bass = Slot(channel_name=ChannelName.TRIANGLE, kind=TRIANGLE, drive=drive)
        lead = Slot(channel_name=ChannelName.PULSE1, kind=PULSE, drive=LOUDER_DRIVE)
        layout = StemLayout(stem_id=0, slots=(lead, bass), cap=2)

        assert layout.gain(1) == 1.0


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


class TestTheOrdersWithinGroups(BaseTestSuite):
    """A combination sounds the same in every order of its rows within each group, so it may be read in each."""

    def test_pulses_driven_alike_stand_in_both_orders_their_own_first(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        (layout,) = separate_layouts(
            _stems({0: [ChannelName.PULSE1, ChannelName.PULSE2, ChannelName.TRIANGLE]}, channel_cap=3), all_channels
        )

        assert layout.orders(["lead", "harmony", "bass"]) == [
            ("lead", "harmony", "bass"),
            ("harmony", "lead", "bass"),
        ]

    def test_pulses_driven_apart_or_alone_keep_their_own_order(
        self, all_channels: Dict[ChannelName, GeneratorUnion]
    ) -> None:
        alone = StemLayout.of(
            _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE]}, channel_cap=2).entries[0], all_channels
        )

        assert StemLayout.of(_driven_apart(), all_channels).orders(["lead", "harmony", "bass"]) == [
            ("lead", "harmony", "bass")
        ]
        assert alone.orders(["lead", "bass"]) == [("lead", "bass")]
