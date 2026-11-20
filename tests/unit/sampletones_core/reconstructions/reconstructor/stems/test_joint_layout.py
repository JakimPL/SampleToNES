from typing import Dict, List

import pytest

from sampletones_core.constants.enums import ChannelName, GeneratorClassName, HierarchyMode, bending_channels
from sampletones_core.generators import GeneratorUnion
from sampletones_core.reconstructions.reconstructor.stems.assignment.joint.layout import StemLayout, separate_layouts
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_core.reconstructions.reconstructor.stems.configs.entry import StemEntry
from sampletones_core.reconstructions.reconstructor.stems.configs.hierarchy import StemsHierarchy
from sampletones_core.reconstructions.reconstructor.stems.configs.settings import StemSettings


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


class TestStemLayout:
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
        assert layout.kinds == {GeneratorClassName.PULSE_GENERATOR, GeneratorClassName.TRIANGLE_GENERATOR}
        assert len(layout.of_kind(GeneratorClassName.PULSE_GENERATOR)) == 2
        assert layout.cap == 2

    def test_a_layout_names_only_channels_the_run_plays(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.NOISE]}, channel_cap=2)
        played = {name: all_channels[name] for name in (ChannelName.PULSE1,)}

        layout = StemLayout.of(stems.entries[0], played)

        assert [slot.channel_name for slot in layout.slots] == [ChannelName.PULSE1]

    def test_two_stems_allowing_one_channel_are_refused(self, all_channels: Dict[ChannelName, GeneratorUnion]) -> None:
        stems = _stems({0: [ChannelName.PULSE1, ChannelName.TRIANGLE], 1: [ChannelName.PULSE1]}, channel_cap=1)

        with pytest.raises(ValueError, match="one stem"):
            separate_layouts(stems, all_channels)
