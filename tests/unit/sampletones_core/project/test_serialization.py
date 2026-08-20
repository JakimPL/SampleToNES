import pytest
from pydantic import ValidationError

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_shared.constants.project import (
    MAX_ROWS_PER_PATTERN,
    MIN_ROWS_PER_PATTERN,
)


def _pattern_with_instrument() -> Pattern:
    pattern = Pattern.empty(4, name="intro")
    pattern.rows[0] = Row(
        transpose=0,
        volume=15,
        instrument=Instrument(
            sample_id="abc123",
            channel_name=ChannelName.PULSE1,
        ),
    )
    return pattern


class TestPatternSerialization:
    def test_round_trip_preserves_name_rows(self) -> None:
        pattern = _pattern_with_instrument()
        restored = Pattern.model_validate(pattern.model_dump())
        assert restored.name == pattern.name
        assert restored.rows == pattern.rows

    def test_dump_round_trips_identically(self) -> None:
        pattern = _pattern_with_instrument()
        dump = pattern.model_dump()
        assert Pattern.model_validate(dump).model_dump() == dump


class TestChannelSerialization:
    def _channel(self) -> Channel:
        return Channel(
            name=ChannelName.PULSE1,
            patterns={0: Pattern.empty(4, name="a"), 1: Pattern.empty(4, name="b")},
        )

    def test_round_trip_preserves_patterns(self) -> None:
        channel = self._channel()
        dump = channel.model_dump()
        restored = Channel.model_validate(dump)
        assert restored.model_dump() == dump
        assert set(restored.patterns) == set(channel.patterns)

    def test_pattern_lookup_after_round_trip(self) -> None:
        channel = self._channel()
        restored = Channel.model_validate(channel.model_dump())
        assert restored.pattern(0) is not None
        assert restored.pattern(0).name == "a"
        assert restored.pattern(1).name == "b"


class TestSongSerialization:
    def test_round_trip(self) -> None:
        song = Song.empty(rows_per_pattern=8)
        dump = song.model_dump()
        assert Song.model_validate(dump).model_dump() == dump

    def test_json_round_trip(self) -> None:
        song = Song.empty(rows_per_pattern=8)
        dump = song.model_dump()
        restored = Song.model_validate_json(song.model_dump_json())
        assert restored.model_dump() == dump

    def test_channels_preserved(self) -> None:
        song = Song.empty(rows_per_pattern=8)
        restored = Song.model_validate(song.model_dump())
        assert set(restored.channels) == set(ChannelName.items())

    def test_order_preserved(self) -> None:
        song = Song.empty(rows_per_pattern=8)
        song.append_frame()
        song.set_order_entry(1, ChannelName.PULSE1, 0)
        restored = Song.model_validate(song.model_dump())
        assert restored.order == song.order
        assert restored.rows_per_pattern == song.rows_per_pattern


class TestSongRowsPerPatternBounds:
    def test_min_rows_per_pattern_accepted(self) -> None:
        song = Song.empty(rows_per_pattern=MIN_ROWS_PER_PATTERN)
        assert song.rows_per_pattern == MIN_ROWS_PER_PATTERN

    def test_max_rows_per_pattern_accepted(self) -> None:
        song = Song.empty(rows_per_pattern=MAX_ROWS_PER_PATTERN)
        assert song.rows_per_pattern == MAX_ROWS_PER_PATTERN

    def test_below_min_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Song.empty(rows_per_pattern=MIN_ROWS_PER_PATTERN - 1)

    def test_above_max_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Song.empty(rows_per_pattern=MAX_ROWS_PER_PATTERN + 1)
