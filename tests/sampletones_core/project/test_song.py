import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import GeneratorName
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


def _place_instrument(song: Song, generator: GeneratorName, sample_id: str, row_index: int = 0) -> None:
    pattern = song.pattern(generator, 0)
    assert pattern is not None
    pattern.rows[row_index] = Row(instrument=Instrument(sample_id=sample_id, generator_name=generator))


class TestSongEmpty:
    def test_creates_one_frame_order(self) -> None:
        song = _song()
        assert song.order_length() == 1

    def test_first_frame_maps_all_channels_to_zero(self) -> None:
        song = _song()
        frame = song.order[0]
        for generator in GeneratorName.items():
            assert frame[generator] == 0

    def test_all_channels_present(self) -> None:
        song = _song()
        for generator in GeneratorName.items():
            assert generator in song.channels

    def test_rows_per_pattern_stored(self) -> None:
        song = Song.empty(16)
        assert song.rows_per_pattern == 16


class TestSongGetItem:
    def test_getitem_returns_channel(self) -> None:
        song = _song()
        channel = song[GeneratorName.PULSE1]
        assert channel.generator == GeneratorName.PULSE1


class TestSongPattern:
    def test_pattern_returns_pattern_at_index(self) -> None:
        song = _song()
        pattern = song.pattern(GeneratorName.PULSE1, 0)
        assert pattern is not None
        assert len(pattern.rows) == _ROWS

    def test_pattern_returns_none_for_missing_index(self) -> None:
        song = _song()
        assert song.pattern(GeneratorName.PULSE1, 99) is None


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
        for generator in GeneratorName.items():
            assert frame[generator] is None

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
        for generator in GeneratorName.items():
            assert song.order[0][generator] is None
            assert song.order[1][generator] == 0

    def test_insert_at_end_appends_none_frame(self) -> None:
        song = _song()
        song.insert_frame(1)
        assert song.order_length() == 2
        for generator in GeneratorName.items():
            assert song.order[1][generator] is None


class TestSongRemoveFrame:
    def test_remove_frame_decrements_order_length(self) -> None:
        song = _song()
        song.append_frame()
        song.remove_frame(1)
        assert song.order_length() == 1

    def test_remove_frame_at_zero_removes_first(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, GeneratorName.PULSE1, 3)
        song.remove_frame(0)
        assert song.order[0][GeneratorName.PULSE1] == 3

    def test_remove_only_frame_leaves_empty_order(self) -> None:
        song = _song()
        song.remove_frame(0)
        assert song.order_length() == 0


class TestSongSetOrderEntry:
    def test_set_order_entry_updates_value(self) -> None:
        song = _song()
        song.set_order_entry(0, GeneratorName.TRIANGLE, 5)
        assert song.order[0][GeneratorName.TRIANGLE] == 5

    def test_set_order_entry_to_none(self) -> None:
        song = _song()
        song.set_order_entry(0, GeneratorName.PULSE1, None)
        assert song.order[0][GeneratorName.PULSE1] is None


class TestSongMoveFrame:
    def test_move_frame_reorders(self) -> None:
        song = _song()
        song.append_frame()
        song.append_frame()
        song.set_order_entry(0, GeneratorName.PULSE1, 1)
        song.set_order_entry(1, GeneratorName.PULSE1, 2)
        song.set_order_entry(2, GeneratorName.PULSE1, 3)

        song.move_frame(0, 2)

        assert song.order[0][GeneratorName.PULSE1] == 2
        assert song.order[1][GeneratorName.PULSE1] == 3
        assert song.order[2][GeneratorName.PULSE1] == 1

    def test_move_frame_no_op_when_same_position(self) -> None:
        song = _song()
        song.set_order_entry(0, GeneratorName.PULSE1, 7)
        song.move_frame(0, 0)
        assert song.order[0][GeneratorName.PULSE1] == 7


class TestSongOrderedPatterns:
    def test_ordered_patterns_returns_pattern_objects(self) -> None:
        song = _song()
        patterns = song.ordered_patterns(GeneratorName.PULSE1)
        assert len(patterns) == 1
        assert patterns[0] is not None

    def test_ordered_patterns_returns_none_for_none_slot(self) -> None:
        song = _song()
        song.append_frame()
        patterns = song.ordered_patterns(GeneratorName.PULSE1)
        assert patterns[1] is None

    def test_ordered_patterns_same_index_repeated_returns_same_object(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, GeneratorName.PULSE1, 0)
        patterns = song.ordered_patterns(GeneratorName.PULSE1)
        assert patterns[0] is patterns[1]


class TestSongRemovePattern:
    def test_remove_pattern_clears_order_references(self) -> None:
        song = _song()
        song.append_frame()
        song.set_order_entry(1, GeneratorName.PULSE1, 0)

        song.remove_pattern(GeneratorName.PULSE1, 0)

        assert song.order[0][GeneratorName.PULSE1] is None
        assert song.order[1][GeneratorName.PULSE1] is None

    def test_remove_pattern_does_not_affect_other_channels(self) -> None:
        song = _song()
        song.remove_pattern(GeneratorName.PULSE1, 0)
        assert song.order[0][GeneratorName.TRIANGLE] == 0

    def test_remove_nonexistent_pattern_raises(self) -> None:
        song = _song()
        with pytest.raises(KeyError):
            song.remove_pattern(GeneratorName.PULSE1, 99)


class TestSongReferencesSample:
    def test_false_when_no_row_references_any_sample(self) -> None:
        assert _song().references_sample("abc") is False

    def test_true_when_a_row_references_the_sample(self) -> None:
        song = _song()
        _place_instrument(song, GeneratorName.PULSE1, "abc")
        assert song.references_sample("abc") is True

    def test_false_for_a_different_sample_id(self) -> None:
        song = _song()
        _place_instrument(song, GeneratorName.PULSE1, "abc")
        assert song.references_sample("xyz") is False


class TestSongClearSampleReferences:
    def test_clears_only_rows_referencing_the_target(self) -> None:
        song = _song()
        _place_instrument(song, GeneratorName.PULSE1, "abc", row_index=0)
        _place_instrument(song, GeneratorName.PULSE1, "keep", row_index=1)

        song.clear_sample_references("abc")

        pattern = song.pattern(GeneratorName.PULSE1, 0)
        assert pattern is not None
        assert pattern.rows[0].instrument is None
        assert pattern.rows[1].instrument is not None

    def test_clears_references_across_all_channels(self) -> None:
        song = _song()
        _place_instrument(song, GeneratorName.PULSE1, "abc")
        _place_instrument(song, GeneratorName.TRIANGLE, "abc")

        song.clear_sample_references("abc")

        assert song.references_sample("abc") is False

    def test_leaves_rows_untouched_when_sample_absent(self) -> None:
        song = _song()
        _place_instrument(song, GeneratorName.PULSE1, "abc")

        song.clear_sample_references("missing")

        pattern = song.pattern(GeneratorName.PULSE1, 0)
        assert pattern is not None
        assert pattern.rows[0].instrument is not None


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
