from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project.instruments.instrument import Instrument
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song


def _pattern_with_instrument() -> Pattern:
    pattern = Pattern.empty(4, name="intro")
    pattern.rows[0] = Row(
        transpose=0,
        volume=15,
        instrument=Instrument(
            sample_id="abc123",
            generator_name=GeneratorName.PULSE1,
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
            generator=GeneratorName.PULSE1,
            patterns={0: Pattern.empty(4, name="a"), 1: Pattern.empty(4, name="b")},
            order=[0, 1, 0],
        )

    def test_round_trip_preserves_patterns_and_order(self) -> None:
        channel = self._channel()
        dump = channel.model_dump()
        restored = Channel.model_validate(dump)
        assert restored.model_dump() == dump
        assert restored.order == channel.order
        assert set(restored.patterns) == set(channel.patterns)

    def test_order_resolves_after_round_trip(self) -> None:
        channel = self._channel()
        restored = Channel.model_validate(channel.model_dump())
        first_index = restored.order[0]
        assert restored.pattern(first_index) is restored.ordered_patterns()[0]


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
        assert set(restored.channels) == set(GeneratorName.items())
