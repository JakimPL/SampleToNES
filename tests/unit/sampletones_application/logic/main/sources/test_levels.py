from pathlib import Path
from typing import List, Sequence

import pytest

from sampletones_application.constants.conversion import MAX_STEM_SOURCES
from sampletones_application.logic.main.sources.levels import MixLevels


def _path(name: str) -> Path:
    return Path(f"/audio/{name}.wav")


def _levels(*names: Sequence[str]) -> MixLevels:
    return MixLevels.of([[_path(name) for name in level] for level in names])


def _shape(levels: MixLevels) -> List[List[str]]:
    return [[path.stem for path in level] for level in levels.levels]


class TestGathering:
    """The mix a reader builds: recordings arrive on the first level and leave without a trace."""

    def test_the_first_recording_opens_a_level(self) -> None:
        assert _shape(MixLevels().add(_path("bass"))) == [["bass"]]

    def test_further_recordings_join_the_first_level(self) -> None:
        levels = MixLevels().add(_path("bass")).add(_path("lead"))
        assert _shape(levels) == [["bass", "lead"]]

    def test_a_recording_already_gathered_changes_nothing(self) -> None:
        assert _shape(_levels(["bass"]).add(_path("bass"))) == [["bass"]]

    def test_removing_the_last_of_a_level_takes_the_level_with_it(self) -> None:
        assert _shape(_levels(["bass"], ["lead"]).remove(_path("bass"))) == [["lead"]]

    def test_keeping_the_first_leaves_the_recording_that_picks_first(self) -> None:
        assert _shape(_levels(["bass", "lead"], ["pad"]).keep_first()) == [["bass"]]

    def test_a_row_states_where_it_stands(self) -> None:
        levels = _levels(["bass", "lead"], ["pad"])
        assert (levels.level_of(_path("lead")), levels.position_of(_path("lead"))) == (0, 1)

    def test_asking_after_a_recording_that_was_never_gathered_fails(self) -> None:
        with pytest.raises(KeyError):
            _levels(["bass"]).level_of(_path("lead"))


class TestTheCeilingAMixHolds:
    """A mix reaches as many recordings as the assignment has room to mix."""

    def test_an_empty_mix_has_room_for_the_whole_ceiling(self) -> None:
        assert MixLevels().room == MAX_STEM_SOURCES

    def test_room_falls_as_recordings_are_gathered(self) -> None:
        assert _levels(["a", "b"]).room == MAX_STEM_SOURCES - 2

    def test_a_recording_arriving_at_a_full_mix_leaves_it_as_it_stands(self) -> None:
        levels = MixLevels()
        for index in range(MAX_STEM_SOURCES):
            levels = levels.add(_path(f"source{index}"))

        assert levels.count == MAX_STEM_SOURCES
        assert levels.add(_path("one_more")).count == MAX_STEM_SOURCES


class TestMovesWithinALevel:
    """Position among peers settles which of two equal-cost choices picks first."""

    def test_a_recording_moves_past_its_neighbor(self) -> None:
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
        assert _shape(_levels(["bass", "lead"], ["pad"]).isolate(_path("bass"))) == [
            ["lead"],
            ["bass"],
            ["pad"],
        ]

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
