from dataclasses import dataclass, replace
from typing import Dict, Final, Sequence, Tuple

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_tools.tracker_playback.comparison import (
    SoundField,
    compare_traces,
    differing_fields,
)
from sampletones_tools.tracker_playback.trace.sound import ChannelSound, SongTrace, TickPosition
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

TONE: Final[ChannelSound] = ChannelSound(audible=True, period=427, volume=15, timbre=2)
SILENT: Final[ChannelSound] = ChannelSound(audible=False, period=0, volume=0, timbre=0)
ROW_TICKS: Final[int] = 2
EXAMPLES: Final[int] = 3


def _trace(pulse: Sequence[ChannelSound], rows: Sequence[int]) -> SongTrace:
    """A trace sounding ``pulse`` on the first pulse channel, the rest silent, a row every ``ROW_TICKS``."""
    positions = tuple(TickPosition(frame=0, row=row) for row in rows)
    channels: Dict[ChannelName, Tuple[ChannelSound, ...]] = {
        channel: tuple(pulse) if channel == ChannelName.PULSE1 else (SILENT,) * len(positions)
        for channel in ChannelName.items()
    }
    return SongTrace(positions=positions, channels=channels)


def _rows(ticks: int) -> Tuple[int, ...]:
    return tuple(tick // ROW_TICKS for tick in range(ticks))


class TestDifferingFields(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        application: ChannelSound
        engine: ChannelSound
        expected: Tuple[SoundField, ...]

    test_cases: Tuple[TestCase, ...] = (
        TestCase(label="alike", application=TONE, engine=TONE, expected=()),
        TestCase(
            label="silent on both sides whatever the registers hold",
            application=replace(SILENT, period=2047),
            engine=replace(SILENT, period=5, volume=3),
            expected=(),
        ),
        TestCase(
            label="sounding on one side alone",
            application=TONE,
            engine=replace(TONE, audible=False, period=5),
            expected=(SoundField.AUDIBLE,),
        ),
        TestCase(
            label="every register",
            application=TONE,
            engine=ChannelSound(audible=True, period=428, volume=5, timbre=1),
            expected=(SoundField.PERIOD, SoundField.VOLUME, SoundField.TIMBRE),
        ),
        TestCase(
            label="the volume alone",
            application=TONE,
            engine=replace(TONE, volume=5),
            expected=(SoundField.VOLUME,),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_fields_that_differ(self, test_case: TestCase) -> None:
        assert differing_fields(test_case.application, test_case.engine) == test_case.expected


class TestCompareTraces:
    def test_alike_traces_match(self) -> None:
        trace = _trace((TONE,) * 4, _rows(4))

        comparison = compare_traces(trace, trace, examples=EXAMPLES)

        assert comparison.matches
        assert (comparison.application_ticks, comparison.engine_ticks) == (4, 4)

    def test_ticks_differing_in_the_same_fields_share_a_divergence_counting_them(self) -> None:
        application = _trace((TONE,) * 4, _rows(4))
        engine = _trace((TONE, replace(TONE, volume=5), replace(TONE, volume=5), replace(TONE, volume=4)), _rows(4))

        comparison = compare_traces(application, engine, examples=EXAMPLES)

        assert not comparison.matches
        (divergence,) = comparison.divergences
        assert (divergence.channel, divergence.fields, divergence.ticks) == (
            ChannelName.PULSE1,
            (SoundField.VOLUME,),
            3,
        )
        assert divergence.first.tick == 1
        assert divergence.first.position == TickPosition(frame=0, row=0)
        assert (divergence.first.application, divergence.first.engine) == (TONE, replace(TONE, volume=5))

    def test_a_later_row_sounding_new_values_joins_the_examples(self) -> None:
        application = _trace((TONE,) * 6, _rows(6))
        engine = _trace(
            (
                replace(TONE, period=428),
                replace(TONE, period=428),
                replace(TONE, period=428),
                replace(TONE, period=428),
                replace(TONE, period=500),
                replace(TONE, period=501),
            ),
            _rows(6),
        )

        (divergence,) = compare_traces(application, engine, examples=EXAMPLES).divergences

        assert [example.tick for example in divergence.examples] == [0, 4]
        assert divergence.ticks == 6

    def test_the_examples_stop_at_their_limit(self) -> None:
        ticks = 2 * EXAMPLES * ROW_TICKS
        application = _trace((TONE,) * ticks, _rows(ticks))
        engine = _trace(tuple(replace(TONE, period=tick) for tick in range(ticks)), _rows(ticks))

        (divergence,) = compare_traces(application, engine, examples=EXAMPLES).divergences

        assert len(divergence.examples) == EXAMPLES
        assert divergence.ticks == ticks

    def test_divergences_are_listed_in_the_order_they_first_show(self) -> None:
        application = _trace((TONE,) * 4, _rows(4))
        engine = _trace((TONE, TONE, replace(TONE, volume=3), SILENT), _rows(4))

        comparison = compare_traces(application, engine, examples=EXAMPLES)

        assert [divergence.fields for divergence in comparison.divergences] == [
            (SoundField.VOLUME,),
            (SoundField.AUDIBLE,),
        ]

    def test_a_song_bitphase_plays_longer_is_no_match(self) -> None:
        comparison = compare_traces(
            _trace((TONE,) * 2, _rows(2)),
            _trace((TONE,) * 3, _rows(3)),
            examples=EXAMPLES,
        )

        assert not comparison.divergences
        assert comparison.timing is None
        assert not comparison.matches

    def test_the_first_tick_the_rows_part_is_named(self) -> None:
        application = _trace((TONE,) * 4, (0, 0, 1, 1))
        engine = _trace((TONE,) * 4, (0, 0, 0, 1))

        comparison = compare_traces(application, engine, examples=EXAMPLES)

        assert comparison.timing is not None
        assert comparison.timing.tick == 2
        assert comparison.timing.position == TickPosition(frame=0, row=1)
        assert comparison.timing.engine_position == TickPosition(frame=0, row=0)
        assert not comparison.matches
