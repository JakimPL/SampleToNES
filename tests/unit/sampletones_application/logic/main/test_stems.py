from pathlib import Path
from typing import FrozenSet, List, Sequence

import pytest

from sampletones_application.logic.main.stems import (
    StemLevels,
    StemSource,
    derive_conversion_setup,
    effective_channels,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode

ENABLED: List[ChannelName] = [ChannelName.PULSE1, ChannelName.TRIANGLE, ChannelName.NOISE]


def _path(name: str) -> Path:
    return Path(f"/audio/{name}.wav")


def _source(name: str, channels: FrozenSet[ChannelName] = frozenset(ENABLED)) -> StemSource:
    return StemSource(path=_path(name), channels=channels)


def _levels(*names: Sequence[str]) -> StemLevels:
    return StemLevels.of([[_source(name) for name in level] for level in names])


def _shape(levels: StemLevels) -> List[List[str]]:
    return [[source.path.stem for source in level] for level in levels.levels]


class TestEffectiveChannels:
    def test_a_source_keeps_the_channels_still_enabled(self) -> None:
        source = _source("lead", frozenset({ChannelName.PULSE1, ChannelName.PULSE2}))
        assert effective_channels(source, ENABLED) == [ChannelName.PULSE1]

    def test_a_source_holding_no_enabled_channel_takes_no_part(self) -> None:
        source = _source("lead", frozenset({ChannelName.PULSE2}))
        assert effective_channels(source, ENABLED) == []

    def test_channels_follow_the_order_the_run_enables_them(self) -> None:
        source = _source("lead", frozenset({ChannelName.NOISE, ChannelName.PULSE1}))
        assert effective_channels(source, ENABLED) == [ChannelName.PULSE1, ChannelName.NOISE]


class TestGathering:
    """The list a reader builds: recordings arrive on the first level and leave without a trace."""

    def test_the_first_recording_opens_a_level(self) -> None:
        assert _shape(StemLevels().add(_source("bass"))) == [["bass"]]

    def test_further_recordings_join_the_first_level(self) -> None:
        levels = StemLevels().add(_source("bass")).add(_source("lead"))
        assert _shape(levels) == [["bass", "lead"]]

    def test_a_recording_already_gathered_changes_nothing(self) -> None:
        levels = _levels(["bass"]).add(_source("bass"))
        assert _shape(levels) == [["bass"]]

    def test_removing_the_last_of_a_level_takes_the_level_with_it(self) -> None:
        assert _shape(_levels(["bass"], ["lead"]).remove(_path("bass"))) == [["lead"]]

    def test_leaving_stems_mode_keeps_the_recording_that_picks_first(self) -> None:
        assert _shape(_levels(["bass", "lead"], ["pad"]).keep_first()) == [["bass"]]

    def test_a_row_states_where_it_stands(self) -> None:
        levels = _levels(["bass", "lead"], ["pad"])
        assert (levels.level_of(_path("lead")), levels.position_of(_path("lead"))) == (0, 1)

    def test_asking_after_a_recording_that_was_never_gathered_fails(self) -> None:
        with pytest.raises(KeyError):
            _levels(["bass"]).level_of(_path("lead"))


class TestMovesWithinALevel:
    """Position among peers settles which of two equal-cost choices picks first."""

    def test_a_recording_moves_past_its_neighbour(self) -> None:
        assert _shape(_levels(["bass", "lead"]).move_within_level(_path("lead"), -1)) == [["lead", "bass"]]

    def test_a_move_off_the_end_of_a_level_changes_nothing(self) -> None:
        levels = _levels(["bass", "lead"])
        assert _shape(levels.move_within_level(_path("bass"), -1)) == _shape(levels)


class TestMovesBetweenLevels:
    def test_a_recording_joins_the_level_below(self) -> None:
        assert _shape(_levels(["bass"], ["lead"]).join_level(_path("bass"), 1)) == [["lead", "bass"]]

    def test_a_recording_joins_the_level_above(self) -> None:
        assert _shape(_levels(["bass"], ["lead"]).join_level(_path("lead"), -1)) == [["bass", "lead"]]

    def test_joining_past_the_last_level_changes_nothing(self) -> None:
        levels = _levels(["bass"], ["lead"])
        assert _shape(levels.join_level(_path("lead"), 1)) == _shape(levels)

    def test_a_recording_takes_a_level_of_its_own_after_the_one_it_shared(self) -> None:
        assert _shape(_levels(["bass", "lead"], ["pad"]).isolate(_path("bass"))) == [["lead"], ["bass"], ["pad"]]

    def test_a_recording_already_alone_stays_where_it_is(self) -> None:
        levels = _levels(["bass"], ["lead"])
        assert _shape(levels.isolate(_path("bass"))) == _shape(levels)


class TestDropOntoARow:
    def test_the_dragged_recording_takes_the_place_it_was_dropped_on(self) -> None:
        assert _shape(_levels(["bass"], ["lead", "pad"]).move_onto(_path("bass"), _path("pad"))) == [
            ["lead", "bass", "pad"]
        ]

    def test_dropping_a_recording_on_itself_changes_nothing(self) -> None:
        levels = _levels(["bass", "lead"])
        assert _shape(levels.move_onto(_path("bass"), _path("bass"))) == _shape(levels)


class TestDropOntoAStrip:
    """A strip is the gap between two bands, counted from the one above the first level."""

    @pytest.mark.parametrize(
        ("position", "expected"),
        [
            (0, [["bass"], ["lead"], ["pad"]]),
            (1, [["bass"], ["lead"], ["pad"]]),
            (2, [["lead"], ["bass"], ["pad"]]),
            (3, [["lead"], ["pad"], ["bass"]]),
        ],
    )
    def test_a_lone_recording_lands_in_the_slot_it_was_dropped_in(
        self,
        position: int,
        expected: List[List[str]],
    ) -> None:
        levels = _levels(["bass"], ["lead"], ["pad"])
        assert _shape(levels.move_to_new_level(_path("bass"), position)) == expected

    @pytest.mark.parametrize(
        ("position", "expected"),
        [
            (0, [["bass"], ["lead"], ["pad"]]),
            (1, [["lead"], ["bass"], ["pad"]]),
            (2, [["lead"], ["pad"], ["bass"]]),
        ],
    )
    def test_a_recording_leaving_its_peers_opens_a_level(
        self,
        position: int,
        expected: List[List[str]],
    ) -> None:
        levels = _levels(["bass", "lead"], ["pad"])
        assert _shape(levels.move_to_new_level(_path("bass"), position)) == expected


class TestDeriveConversionSetup:
    def test_a_recordings_position_is_its_stem_id(self) -> None:
        setup = derive_conversion_setup(
            _levels(["a", "b"]),
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert [entry.id for entry in setup.stems.entries] == [0, 1]

    def test_recordings_sharing_a_level_pick_together(self) -> None:
        setup = derive_conversion_setup(
            _levels(["a", "c"], ["b"]),
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.hierarchy.levels == [[0, 1], [2]]

    def test_the_mix_lists_the_recordings_in_entry_order(self) -> None:
        setup = derive_conversion_setup(
            _levels(["a"], ["b"]),
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert setup.sources == (_path("a"), _path("b"))

    def test_a_recording_holding_no_enabled_channel_reaches_neither_the_mix_nor_the_entries(self) -> None:
        levels = StemLevels.of([[_source("a"), _source("silent", frozenset())], [_source("b")]])

        setup = derive_conversion_setup(
            levels,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.sources == (_path("a"), _path("b"))
        assert setup.stems.hierarchy.levels == [[0], [1]]

    def test_a_level_left_with_nobody_taking_part_drops_out(self) -> None:
        levels = StemLevels.of([[_source("silent", frozenset())], [_source("b")]])

        setup = derive_conversion_setup(
            levels,
            ENABLED,
            channel_cap=1,
            hierarchy_mode=HierarchyMode.STRICT,
        )

        assert setup.stems.hierarchy.levels == [[0]]

    def test_the_cap_and_the_mode_travel_with_the_setup(self) -> None:
        setup = derive_conversion_setup(
            _levels(["a"]),
            ENABLED,
            channel_cap=2,
            hierarchy_mode=HierarchyMode.ROUND_ROBIN,
        )

        assert (setup.stems.channel_cap, setup.stems.hierarchy.mode) == (2, HierarchyMode.ROUND_ROBIN)
