import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_shared.constants.project import (
    DEFAULT_ROWS_PER_PATTERN,
    MAX_ROWS_PER_PATTERN,
    MIN_ROWS_PER_PATTERN,
)

_ROWS = DEFAULT_ROWS_PER_PATTERN


def _song(rows_per_pattern: int = _ROWS) -> Song:
    return Song.empty(rows_per_pattern)


def _place_instrument(song: Song, channel: ChannelName, sample_id: str, row_index: int = 0) -> None:
    pattern = song.pattern(channel, 0)
    assert pattern is not None
    pattern.rows[row_index] = Row(command=Instrument(sample_id=sample_id, channel_name=channel))


class TestSongEmpty:
    def test_creates_one_frame_order(self) -> None:
        song = _song()
        assert song.order_length() == 1

    def test_first_frame_maps_all_channels_to_zero(self) -> None:
        song = _song()
        frame = song.order[0]
        for channel in ChannelName.items():
            assert frame[channel] == 0

    def test_all_channels_present(self) -> None:
        song = _song()
        for channel in ChannelName.items():
            assert channel in song.channels

    def test_rows_per_pattern_stored(self) -> None:
        song = Song.empty(16)
        assert song.rows_per_pattern == 16


class TestSongGetItem:
    def test_getitem_returns_channel(self) -> None:
        song = _song()
        channel = song[ChannelName.PULSE1]
        assert channel.name == ChannelName.PULSE1


class TestSongPattern:
    def test_pattern_returns_pattern_at_index(self) -> None:
        song = _song()
        pattern = song.pattern(ChannelName.PULSE1, 0)
        assert pattern is not None
        assert len(pattern.rows) == _ROWS

    def test_pattern_returns_none_for_missing_index(self) -> None:
        song = _song()
        assert song.pattern(ChannelName.PULSE1, 99) is None


class TestSongOrderLength:
    def test_order_length_grows_after_append(self) -> None:
        song = _song()
        song.append_frame()
        assert song.order_length() == 2


class TestSongAppendFrame:
    def test_append_adds_frame_with_all_none(self) -> None:
        song = _song()
        song.append_frame()
        frame = song.order[1]
        for channel in ChannelName.items():
            assert frame[channel] is None

    def test_append_increments_order_length(self) -> None:
        song = _song()
        for i in range(5):
            song.append_frame()
        assert song.order_length() == 6


class TestSongInsertFrame:
    def test_insert_at_zero_shifts_existing_frame(self) -> None:
        song = _song()
        song.insert_frame(0)
        assert song.order_length() == 2
        for channel in ChannelName.items():
            assert song.order[0][channel] is None
            assert song.order[1][channel] == 0

    def test_insert_at_end_appends_none_frame(self) -> None:
        song = _song()
        song.insert_frame(1)
        assert song.order_length() == 2
        for channel in ChannelName.items():
            assert song.order[1][channel] is None


class TestSongRemoveFrame:
    def test_remove_frame_decrements_order_length(self) -> None:
        song = _song()
        song.append_frame()
        song.remove_frame(1)
        assert song.order_length() == 1

    def test_remove_frame_at_zero_removes_first(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 3)
        song.remove_frame(0)
        assert song.order[0][ChannelName.PULSE1] == 3

    def test_remove_only_frame_leaves_empty_order(self) -> None:
        song = _song()
        song.remove_frame(0)
        assert song.order_length() == 0


class TestSongSetOrderEntry:
    def test_set_order_entry_updates_value(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.TRIANGLE, 5)
        assert song.order[0][ChannelName.TRIANGLE] == 5

    def test_set_order_entry_to_none(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.PULSE1, None)
        assert song.order[0][ChannelName.PULSE1] is None


class TestSongMoveFrame:
    def test_move_frame_reorders(self) -> None:
        song = _song()
        song.append_frame()
        song.append_frame()
        song.set_order_entry(0, ChannelName.PULSE1, 1)
        song.set_order_entry(1, ChannelName.PULSE1, 2)
        song.set_order_entry(2, ChannelName.PULSE1, 3)

        song.move_frame(0, 2)

        assert song.order[0][ChannelName.PULSE1] == 2
        assert song.order[1][ChannelName.PULSE1] == 3
        assert song.order[2][ChannelName.PULSE1] == 1

    def test_move_frame_no_op_when_same_position(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.PULSE1, 7)
        song.move_frame(0, 0)
        assert song.order[0][ChannelName.PULSE1] == 7


class TestSongDuplicateFrame:
    def test_duplicate_inserts_frame_after_position(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 3)

        song.duplicate_frame(0)

        assert song.order_length() == 3
        assert song.order[2][ChannelName.PULSE1] == 3

    def test_duplicate_points_channels_at_the_same_patterns(self) -> None:
        song = _song()

        song.duplicate_frame(0)

        source_index = song.order[0][ChannelName.PULSE1]
        duplicate_index = song.order[1][ChannelName.PULSE1]
        assert duplicate_index == source_index

    def test_duplicate_allocates_no_pattern(self) -> None:
        song = _song()
        pattern_count = len(song[ChannelName.PULSE1].patterns)

        song.duplicate_frame(0)

        assert len(song[ChannelName.PULSE1].patterns) == pattern_count

    def test_editing_a_shared_pattern_is_heard_in_both_frames(self) -> None:
        song = _song()
        song.duplicate_frame(0)
        duplicate_index = song.order[1][ChannelName.PULSE1]
        assert duplicate_index is not None

        _place_instrument(song, ChannelName.PULSE1, "sample-a", row_index=0)

        shared_pattern = song.pattern(ChannelName.PULSE1, duplicate_index)
        assert shared_pattern is not None
        assert shared_pattern.rows[0].command is not None

    def test_repointing_one_frame_leaves_the_other_where_it_was(self) -> None:
        """The copy is a fresh mapping, so the two frames' slots move independently."""
        song = _song()
        song.duplicate_frame(0)

        song.set_order_entry(1, ChannelName.PULSE1, 9)

        assert song.order[0][ChannelName.PULSE1] == 0

    def test_duplicate_carries_an_unmaterialised_index_across(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.PULSE1, 7)

        song.duplicate_frame(0)

        assert song.order[1][ChannelName.PULSE1] == 7
        assert song.pattern(ChannelName.PULSE1, 7) is None


class TestSongCloneFrame:
    def test_clone_inserts_frame_after_position(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 3)

        song.clone_frame(0)

        assert song.order_length() == 3
        assert song.order[2][ChannelName.PULSE1] == 3

    def test_clone_points_channels_at_fresh_patterns(self) -> None:
        song = _song()

        song.clone_frame(0)

        source_index = song.order[0][ChannelName.PULSE1]
        clone_index = song.order[1][ChannelName.PULSE1]
        assert clone_index != source_index

    def test_clone_avoids_indices_referenced_by_other_frames(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 7)

        song.clone_frame(0)

        clone_index = song.order[1][ChannelName.PULSE1]
        assert clone_index != 7

    def test_editing_a_cloned_pattern_leaves_the_source_untouched(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "sample-a", row_index=0)
        source_index = song.order[0][ChannelName.PULSE1]

        song.clone_frame(0)
        clone_index = song.order[1][ChannelName.PULSE1]
        song[ChannelName.PULSE1].set_row(clone_index, 0, Row())

        source_pattern = song.pattern(ChannelName.PULSE1, source_index)
        assert source_pattern is not None
        assert source_pattern.rows[0].command is not None

    def test_clone_keeps_a_silent_slot_silent(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.NOISE, None)

        song.clone_frame(0)

        assert song.order[1][ChannelName.NOISE] is None


class TestSongPatternAllocation:
    def test_add_pattern_skips_indices_referenced_by_the_order(self) -> None:
        song = _song()
        song.set_order_entry(0, ChannelName.PULSE1, 4)

        index = song.add_pattern(ChannelName.PULSE1)

        assert index != 4
        assert index in song[ChannelName.PULSE1].patterns

    def test_clone_pattern_skips_indices_referenced_by_the_order(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 6)

        clone_index = song.clone_pattern(ChannelName.PULSE1, 0)

        assert clone_index != 6


class TestSongClearFrame:
    def test_clear_frame_sets_all_channels_to_none(self) -> None:
        song = _song()
        for channel in ChannelName.items():
            song.set_order_entry(0, channel, 3)

        song.clear_frame(0)

        assert all(song.order[0][channel] is None for channel in ChannelName.items())

    def test_clear_frame_leaves_other_frames(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(0, ChannelName.PULSE1, 1)
        song.set_order_entry(1, ChannelName.PULSE1, 2)

        song.clear_frame(0)

        assert song.order[0][ChannelName.PULSE1] is None
        assert song.order[1][ChannelName.PULSE1] == 2


class TestSongOrderedPatterns:
    def test_ordered_patterns_returns_pattern_objects(self) -> None:
        song = _song()
        patterns = song.ordered_patterns(ChannelName.PULSE1)
        assert len(patterns) == 1
        assert patterns[0] is not None

    def test_ordered_patterns_returns_none_for_none_slot(self) -> None:
        song = _song()
        song.append_frame()
        patterns = song.ordered_patterns(ChannelName.PULSE1)
        assert patterns[1] is None

    def test_ordered_patterns_same_index_repeated_returns_same_object(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 0)
        patterns = song.ordered_patterns(ChannelName.PULSE1)
        assert patterns[0] is patterns[1]


class TestSongRemovePattern:
    def test_remove_pattern_clears_order_references(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 0)

        song.remove_pattern(ChannelName.PULSE1, 0)

        assert song.order[0][ChannelName.PULSE1] is None
        assert song.order[1][ChannelName.PULSE1] is None

    def test_remove_pattern_does_not_affect_other_channels(self) -> None:
        song = _song()
        song.remove_pattern(ChannelName.PULSE1, 0)
        assert song.order[0][ChannelName.TRIANGLE] == 0

    def test_remove_nonexistent_pattern_raises(self) -> None:
        song = _song()
        with pytest.raises(KeyError):
            song.remove_pattern(ChannelName.PULSE1, 99)


class TestSongReferencesSample:
    def test_false_when_no_row_references_any_sample(self) -> None:
        assert _song().references_sample("abc") is False

    def test_true_when_a_row_references_the_sample(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "abc")
        assert song.references_sample("abc") is True

    def test_false_for_a_different_sample_id(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "abc")
        assert song.references_sample("xyz") is False


class TestSongClearSampleReferences:
    def test_clears_only_rows_referencing_the_target(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "abc", row_index=0)
        _place_instrument(song, ChannelName.PULSE1, "keep", row_index=1)

        song.clear_sample_references("abc")

        pattern = song.pattern(ChannelName.PULSE1, 0)
        assert pattern is not None
        assert pattern.rows[0].command is None
        assert pattern.rows[1].command is not None

    def test_clears_references_across_all_channels(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "abc")
        _place_instrument(song, ChannelName.TRIANGLE, "abc")

        song.clear_sample_references("abc")

        assert song.references_sample("abc") is False

    def test_leaves_rows_untouched_when_sample_absent(self) -> None:
        song = _song()
        _place_instrument(song, ChannelName.PULSE1, "abc")

        song.clear_sample_references("missing")

        pattern = song.pattern(ChannelName.PULSE1, 0)
        assert pattern is not None
        assert pattern.rows[0].command is not None


class TestSongResizePatterns:
    def test_resize_truncates_longer_patterns(self) -> None:
        song = Song.empty(8)
        song.resize_patterns(4)
        assert song.rows_per_pattern == 4
        for channel in song.channels.values():
            for pattern in channel.patterns.values():
                assert len(pattern.rows) == 4

    def test_resize_extends_shorter_patterns_with_empty_rows(self) -> None:
        song = Song.empty(4)
        song.resize_patterns(8)
        assert song.rows_per_pattern == 8
        for channel in song.channels.values():
            for pattern in channel.patterns.values():
                assert len(pattern.rows) == 8
                for row in pattern.rows[4:]:
                    assert row == Row()

    def test_resize_to_same_length_is_no_op(self) -> None:
        song = Song.empty(8)
        song.resize_patterns(8)
        assert song.rows_per_pattern == 8
        for channel in song.channels.values():
            for pattern in channel.patterns.values():
                assert len(pattern.rows) == 8


class TestSongValidation:
    def test_zero_rows_per_pattern_raises(self) -> None:
        with pytest.raises(ValidationError):
            Song.empty(0)

    def test_resize_above_maximum_raises_and_leaves_song_unchanged(self) -> None:
        """``resize_patterns`` assigns ``rows_per_pattern``, so its bounds must hold on mutation too."""
        song = Song.empty(8)
        with pytest.raises(ValidationError):
            song.resize_patterns(MAX_ROWS_PER_PATTERN + 1)

        assert song.rows_per_pattern == 8

    def test_resize_below_minimum_raises(self) -> None:
        song = Song.empty(8)
        with pytest.raises(ValidationError):
            song.resize_patterns(MIN_ROWS_PER_PATTERN - 1)

    def test_rows_per_pattern_above_max_raises(self) -> None:
        with pytest.raises(ValidationError):
            Song.empty(257)


@pytest.mark.parametrize("rows", [1, 16, 64, 256])
def test_empty_song_valid_for_boundary_row_counts(rows: int) -> None:
    song = Song.empty(rows)
    assert song.rows_per_pattern == rows


def test_repr_includes_order_length_and_rows_per_pattern() -> None:
    song = Song.empty(16)
    text = repr(song)
    assert "order_length=1" in text
    assert "rows_per_pattern=16" in text
