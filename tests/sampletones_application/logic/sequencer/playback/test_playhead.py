import pytest

from sampletones_application.logic.sequencer.playback.playhead import (
    remap_after_insert,
    remap_after_move,
    remap_after_remove,
)


class TestRemapAfterInsert:
    @pytest.mark.parametrize(
        "playhead, inserted_index, expected",
        [
            (3, 0, 4),  # inserted before the playhead → shifts one later
            (3, 3, 4),  # inserted at the playhead → shifts one later
            (3, 4, 3),  # inserted after the playhead → unchanged
            (0, 5, 0),  # appended far ahead → unchanged
        ],
    )
    def test_remap(self, playhead: int, inserted_index: int, expected: int) -> None:
        assert remap_after_insert(playhead, inserted_index) == expected


class TestRemapAfterRemove:
    @pytest.mark.parametrize(
        "playhead, removed_index, new_length, expected",
        [
            (3, 0, 4, 2),  # removed before the playhead → one earlier
            (3, 5, 4, 3),  # removed after the playhead → unchanged
            (3, 3, 4, 3),  # removed the playing frame, more remain → same index (the next frame)
            (3, 3, 3, 2),  # removed the playing last frame → clamps to the new last
            (0, 0, 0, 0),  # removed the only frame → pinned at 0
        ],
    )
    def test_remap(self, playhead: int, removed_index: int, new_length: int, expected: int) -> None:
        assert remap_after_remove(playhead, removed_index, new_length) == expected


class TestRemapAfterMove:
    @pytest.mark.parametrize(
        "playhead, from_index, to_index, expected",
        [
            (2, 2, 5, 5),  # the playing frame follows itself
            (2, 0, 5, 1),  # an earlier frame moved to after → playhead shifts earlier
            (2, 5, 0, 3),  # a later frame moved to before → playhead shifts later
            (2, 4, 5, 2),  # move entirely after the playhead → unchanged
            (3, 0, 1, 3),  # move within the region before the playhead → unchanged
        ],
    )
    def test_remap(self, playhead: int, from_index: int, to_index: int, expected: int) -> None:
        assert remap_after_move(playhead, from_index, to_index) == expected
