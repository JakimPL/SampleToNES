from dataclasses import dataclass
from pathlib import Path
from typing import Final, Tuple

import pytest

from sampletones_player.compression.compressed import CompressedPlanes
from sampletones_player.compression.dictionary.phrase import Phrase
from sampletones_player.compression.dictionary.table import phrase_table
from sampletones_player.compression.encode import emit
from sampletones_player.compression.pitch import PitchTable
from sampletones_player.compression.planes.order import PlaneOrder
from sampletones_player.compression.planes.song import SongPlanes
from sampletones_player.compression.tokens.hold import HoldToken
from sampletones_player.compression.tokens.literal import LiteralToken
from sampletones_player.specification.compression import PLANE_COUNT
from sampletones_shared.music import Tuning
from sampletones_tools.codec.study.corpus.song import SongGroup, StudySong
from sampletones_tools.codec.study.measure import Measurement, production_encoding
from sampletones_tools.codec.study.variants.seeds import split, trimmed, whole_and_split
from sampletones_tools.codec.study.variants.strategy import DEPTH_PREFIX, depth_measurements
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.study import NO_STUDY_SLICES, lowest_notes

TICKS: Final[int] = 4
BASELINE: Final[str] = "baseline"
TRIMMED: Final[str] = "seeds-trimmed"
WIDE: Final[str] = "search-wide"
ORDER: Final[Tuple[str, ...]] = (BASELINE, TRIMMED, "seeds-split-4", WIDE)


class TestTrimmed(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        body: bytes
        expected: bytes

    test_cases = (
        TestCase(
            label="a trailing plateau ends at its first value", body=b"\x01\x02\x03\x03\x03", expected=b"\x01\x02\x03"
        ),
        TestCase(label="a body of one value keeps one", body=b"\x05\x05", expected=b"\x05"),
        TestCase(label="a body moving to its end stays", body=b"\x01\x02", expected=b"\x01\x02"),
        TestCase(label="a plateau inside the body stays", body=b"\x01\x01\x02", expected=b"\x01\x01\x02"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_tail_is_cut(self, test_case: TestCase) -> None:
        assert trimmed((Phrase(body=test_case.body),)) == (Phrase(body=test_case.expected),)


class TestSplit(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        body: bytes
        threshold: int
        expected: Tuple[bytes, ...]

    test_cases = (
        TestCase(
            label="plateaus of three cut the body",
            body=b"\x01\x02\x02\x02\x03\x04\x04\x04\x04\x05",
            threshold=3,
            expected=(b"\x01\x02", b"\x03\x04"),
        ),
        TestCase(
            label="a threshold above every plateau keeps the body whole",
            body=b"\x01\x02\x02\x02\x03",
            threshold=4,
            expected=(b"\x01\x02\x02\x02\x03",),
        ),
        TestCase(
            label="plateaus of two cut too",
            body=b"\x01\x01\x02\x03\x03\x04",
            threshold=2,
            expected=(b"\x02\x03",),
        ),
        TestCase(
            label="a piece of one value is dropped",
            body=b"\x01\x02\x02\x02\x03",
            threshold=3,
            expected=(b"\x01\x02",),
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_the_pieces_end_where_a_plateau_begins(self, test_case: TestCase) -> None:
        assert split((Phrase(body=test_case.body),), test_case.threshold) == tuple(
            Phrase(body=piece) for piece in test_case.expected
        )

    def test_whole_and_split_offers_both(self) -> None:
        seeds = (Phrase(body=b"\x01\x02\x02\x02\x03\x04"),)

        assert whole_and_split(seeds, 3) == (*seeds, Phrase(body=b"\x01\x02"), Phrase(body=b"\x03\x04"))


def _song() -> StudySong:
    return StudySong(
        name="song",
        group=SongGroup.PROJECT,
        source=Path("song.stp"),
        planes=SongPlanes.from_order(PlaneOrder.across([bytes(TICKS)] * PLANE_COUNT)),
        seeds=(),
        pitches=PitchTable.from_tuning(Tuning()),
        notes=lowest_notes(TICKS),
        slices=NO_STUDY_SLICES,
    )


def _measurement(
    song: StudySong,
    variant: str,
    *,
    spelled_out: bool,
    seconds: float,
) -> Measurement:
    stream = emit([LiteralToken(values=bytes(TICKS))] if spelled_out else [HoldToken(ticks=TICKS)])
    compressed = CompressedPlanes(
        phrases=phrase_table(()),
        streams=PlaneOrder.across([stream] * PLANE_COUNT),
        ticks=TICKS,
    )
    return Measurement(
        song=song,
        variant=variant,
        encoding=production_encoding(song, compressed, seconds),
    )


class TestDepthMeasurements:
    def test_each_depth_keeps_the_smallest_so_far_and_sums_the_time(self) -> None:
        song = _song()
        measurements = (
            _measurement(song, BASELINE, spelled_out=True, seconds=1.0),
            _measurement(song, TRIMMED, spelled_out=False, seconds=2.0),
            _measurement(song, WIDE, spelled_out=True, seconds=4.0),
        )

        depths = depth_measurements(measurements, ORDER)

        assert [depth.variant for depth in depths] == [f"{DEPTH_PREFIX}{depth}" for depth in (1, 2, 3)]
        assert [depth.block for depth in depths] == [
            measurements[0].block,
            measurements[1].block,
            measurements[1].block,
        ]
        assert [depth.seconds for depth in depths] == [1.0, 3.0, 7.0]

    def test_a_strategy_no_song_was_measured_under_takes_no_depth(self) -> None:
        song = _song()
        measurements = (_measurement(song, BASELINE, spelled_out=True, seconds=1.0),)

        assert [depth.variant for depth in depth_measurements(measurements, ORDER)] == [f"{DEPTH_PREFIX}1"]
