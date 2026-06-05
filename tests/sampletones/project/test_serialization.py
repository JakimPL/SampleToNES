from sampletones_core.constants.enums import GeneratorName
from sampletones_core.project import (
    Channel,
    Pattern,
    Row,
    Song,
    SubInstrument,
)
from sampletones_core.structures import IndexedCollection


def _pattern_with_subinstrument() -> Pattern:
    pattern = Pattern.empty(4, name="intro")
    pattern.rows[0] = Row(
        pitch=60,
        volume=15,
        subinstrument=SubInstrument(instrument_id="abc123", generator_name=GeneratorName.PULSE1),
    )
    return pattern


class TestPatternSerialization:
    def test_round_trip_preserves_id_name_rows(self) -> None:
        pattern = _pattern_with_subinstrument()
        restored = Pattern.model_validate(pattern.model_dump())
        assert restored.id == pattern.id
        assert restored.name == pattern.name
        assert restored.rows == pattern.rows

    def test_dump_round_trips_identically(self) -> None:
        pattern = _pattern_with_subinstrument()
        dump = pattern.model_dump()
        assert Pattern.model_validate(dump).model_dump() == dump


class TestChannelSerialization:
    def _channel(self) -> Channel:
        first = Pattern.empty(4, name="a")
        second = Pattern.empty(4, name="b")
        patterns: IndexedCollection[Pattern] = IndexedCollection([first, second])
        return Channel(
            generator=GeneratorName.PULSE1,
            patterns=patterns,
            order=[first.id, second.id, first.id],
        )

    def test_round_trip_preserves_patterns_and_order(self) -> None:
        channel = self._channel()
        dump = channel.model_dump()
        restored = Channel.model_validate(dump)
        assert restored.model_dump() == dump
        assert restored.order == channel.order
        assert [pattern.id for pattern in restored.patterns] == [pattern.id for pattern in channel.patterns]

    def test_order_resolves_after_round_trip(self) -> None:
        channel = self._channel()
        restored = Channel.model_validate(channel.model_dump())
        first_id = restored.order[0]
        assert restored.pattern(first_id) is restored.ordered_patterns()[0]


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
