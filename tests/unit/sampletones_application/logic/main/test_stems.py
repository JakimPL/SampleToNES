from pathlib import Path
from typing import FrozenSet, List

from sampletones_application.constants.conversion import DEFAULT_STEM_LEVEL
from sampletones_application.logic.main.stems import (
    StemSource,
    derive_stems_config,
    effective_channels,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

ENABLED: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]


def _source(name: str, channels: FrozenSet[ChannelName], level: int = DEFAULT_STEM_LEVEL) -> StemSource:
    return StemSource(path=Path(f"/audio/{name}.wav"), channels=channels, level=level)


class TestEffectiveChannels:
    def test_a_source_keeps_the_channels_still_enabled(self) -> None:
        source = _source("lead", frozenset({ChannelName.PULSE1, ChannelName.PULSE2}))
        assert effective_channels(source, ENABLED) == [ChannelName.PULSE1]

    def test_a_source_left_with_none_takes_every_enabled_channel(self) -> None:
        source = _source("lead", frozenset({ChannelName.PULSE2}))
        assert effective_channels(source, ENABLED) == ENABLED

    def test_channels_follow_the_order_the_run_enables_them(self) -> None:
        source = _source("lead", frozenset({ChannelName.NOISE, ChannelName.PULSE1}))
        assert effective_channels(source, ENABLED) == [ChannelName.PULSE1, ChannelName.NOISE]


class TestDeriveStemsConfig:
    def test_a_rows_position_is_its_stem_id(self) -> None:
        sources = [_source("a", frozenset(ENABLED)), _source("b", frozenset(ENABLED))]

        setup = derive_stems_config(
            sources,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert [entry.id for entry in setup.entries] == [0, 1]

    def test_rows_sharing_a_level_pick_together(self) -> None:
        sources = [
            _source("a", frozenset(ENABLED), level=1),
            _source("b", frozenset(ENABLED), level=2),
            _source("c", frozenset(ENABLED), level=1),
        ]

        setup = derive_stems_config(
            sources,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.hierarchy.levels == [[0, 2], [1]]

    def test_levels_follow_their_numbers_upwards_with_the_gaps_closed(self) -> None:
        """Levels the reader left unused hold no rows, so the hierarchy names the ones in use."""
        sources = [
            _source("a", frozenset(ENABLED), level=5),
            _source("b", frozenset(ENABLED), level=2),
        ]

        setup = derive_stems_config(
            sources,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert setup.hierarchy.levels == [[1], [0]]

    def test_the_cap_and_the_mode_reach_the_setup(self) -> None:
        setup = derive_stems_config(
            [_source("a", frozenset(ENABLED))],
            ENABLED,
            channel_cap=2,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert setup.channel_cap == 2
        assert setup.hierarchy.mode == HierarchyMode.ROUND_ROBIN

    def test_a_disabled_channel_leaves_the_setup(self) -> None:
        setup = derive_stems_config(
            [_source("a", frozenset({ChannelName.PULSE1, ChannelName.PULSE2}))],
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.entries[0].channels == [ChannelName.PULSE1]
        assert setup.covered_channels == frozenset({ChannelName.PULSE1})

    def test_the_hierarchy_names_every_row(self) -> None:
        """The setup validates that its hierarchy names each stem once, so a derivation that
        dropped one would be refused rather than stored."""
        sources = [_source(name, frozenset(ENABLED), level=level) for name, level in (("a", 1), ("b", 3), ("c", 3))]

        setup = derive_stems_config(
            sources,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        named = [stem_id for level in setup.hierarchy.levels for stem_id in level]
        assert sorted(named) == [entry.id for entry in setup.entries]
