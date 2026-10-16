from typing import Final, List, Tuple

import numpy as np
import pytest

from sampletones_core.audio.output import BufferSource, Fill
from tests.suite.audio.ramp import RAMP_STEP, ramp, ramp_indices

DOCUMENT_RATE: Final[int] = 44100
FASTER_RATE: Final[int] = 48000
HALF_RATE: Final[int] = 22050
BLOCK: Final[int] = 1024
LENGTH: Final[int] = 10 * BLOCK + 300
SEEK_TARGET: Final[int] = 6000
REPLACEMENT_START: Final[int] = 500_000
INTERIOR: Final[int] = 256
PITCH_TOLERANCE: Final[float] = 0.5
LENGTH_TOLERANCE: Final[int] = 2


def _source(audio: np.ndarray, *, sample_rate: int, output_rate: int, start: int) -> BufferSource:
    """A source begun on a stream at ``output_rate``, the way the writer begins one at its first read."""
    source = BufferSource(audio, sample_rate=sample_rate, start=start)
    source.begin(output_rate, _unexpected)
    return source


def _unexpected(error: Exception) -> None:
    raise AssertionError(f"a buffer told a failure between reads: {error}")


def _read(source: BufferSource) -> Tuple[np.ndarray, Fill[int]]:
    block = np.zeros(BLOCK, dtype=np.float32)
    fill = source.read_into(block)
    return block[: fill.frames], fill


def _read_all(source: BufferSource) -> Tuple[np.ndarray, List[Fill[int]]]:
    """Reads blocks until the source runs out, and answers what it played and every fill."""
    played: List[np.ndarray] = []
    fills: List[Fill[int]] = []
    while True:
        samples, fill = _read(source)
        played.append(samples)
        fills.append(fill)
        if fill.frames < BLOCK:
            return np.concatenate(played), fills


def _positions(samples: np.ndarray) -> np.ndarray:
    """The document positions a run of resampled ramp samples stands at, unrounded."""
    return samples.astype(np.float64) / RAMP_STEP


class TestBlocks:
    """A source at the device's rate fills every block whole, short only at the end, sample for sample."""

    def test_every_sample_plays_once_in_order(self) -> None:
        played, fills = _read_all(_source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0))

        np.testing.assert_array_equal(ramp_indices(played), np.arange(LENGTH))
        assert [fill.frames for fill in fills] == [BLOCK] * 10 + [300]

    def test_a_source_run_out_fills_nothing(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read_all(source)

        _, fill = _read(source)

        assert fill.frames == 0
        assert fill.reports == ()

    def test_a_playback_starts_where_it_is_asked_to(self) -> None:
        played, _ = _read(
            _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=SEEK_TARGET)
        )

        assert ramp_indices(played)[0] == SEEK_TARGET

    def test_every_block_reports_the_sample_it_reached(self) -> None:
        _, fills = _read_all(_source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0))

        reached = [fill.reports[0].report for fill in fills if fill.reports]
        assert reached == [*range(BLOCK, 10 * BLOCK + 1, BLOCK), LENGTH]
        assert all(fill.reports[0].offset == fill.frames for fill in fills if fill.reports)


class TestRates:
    """Rule 5: a source made at another rate keeps its pitch and its length on the device."""

    @pytest.mark.parametrize("output_rate", [FASTER_RATE, HALF_RATE])
    def test_a_source_keeps_its_length(self, output_rate: int) -> None:
        played, _ = _read_all(_source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=output_rate, start=0))

        assert abs(len(played) - LENGTH * output_rate / DOCUMENT_RATE) <= LENGTH_TOLERANCE

    @pytest.mark.parametrize("output_rate", [FASTER_RATE, HALF_RATE])
    def test_a_source_keeps_its_pitch(self, output_rate: int) -> None:
        played, _ = _read_all(_source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=output_rate, start=0))

        interior = np.arange(INTERIOR, len(played) - INTERIOR)
        expected = interior * DOCUMENT_RATE / output_rate
        assert np.max(np.abs(_positions(played[interior]) - expected)) < PITCH_TOLERANCE

    def test_a_resampled_block_reports_the_document_sample_it_reached(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=FASTER_RATE, start=0)

        _, fill = _read(source)
        _, second = _read(source)

        assert fill.reports[0].report == round(BLOCK * DOCUMENT_RATE / FASTER_RATE)
        assert second.reports[0].report == round(2 * BLOCK * DOCUMENT_RATE / FASTER_RATE)


class TestSeek:
    """Rule 4: a seek takes effect at the next block, and the block after it reads the seek."""

    def test_a_seek_moves_the_next_block(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)

        source.seek(SEEK_TARGET)
        played, fill = _read(source)

        np.testing.assert_array_equal(ramp_indices(played), np.arange(SEEK_TARGET, SEEK_TARGET + BLOCK))
        assert fill.reports[0].report == SEEK_TARGET + BLOCK

    def test_a_resampled_seek_moves_the_next_block(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=FASTER_RATE, start=0)
        _read(source)

        source.seek(SEEK_TARGET)
        played, fill = _read(source)

        interior = np.arange(INTERIOR, BLOCK - INTERIOR)
        expected = SEEK_TARGET + interior * DOCUMENT_RATE / FASTER_RATE
        assert np.max(np.abs(_positions(played[interior]) - expected)) < PITCH_TOLERANCE
        assert fill.reports[0].report == SEEK_TARGET + round(BLOCK * DOCUMENT_RATE / FASTER_RATE)

    def test_a_seek_past_the_end_runs_the_source_out(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)

        source.seek(2 * LENGTH)
        _, fill = _read(source)

        assert fill.frames == 0


class TestReplace:
    """Rule 4: a replacement takes effect at the next block and keeps the moment the playback reached."""

    def test_a_replacement_plays_on_from_where_the_playback_stood(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)
        _read(source)

        source.replace(ramp(LENGTH, start=REPLACEMENT_START), sample_rate=DOCUMENT_RATE)
        played, _ = _read(source)

        np.testing.assert_array_equal(
            ramp_indices(played),
            np.arange(REPLACEMENT_START + 2 * BLOCK, REPLACEMENT_START + 3 * BLOCK),
        )

    def test_a_replacement_shorter_than_the_position_runs_the_source_out(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)
        _read(source)

        source.replace(ramp(BLOCK), sample_rate=DOCUMENT_RATE)
        _, fill = _read(source)

        assert fill.frames == 0

    def test_a_replacement_at_another_rate_keeps_the_moment(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)
        _read(source)

        source.replace(ramp(LENGTH), sample_rate=HALF_RATE)
        _, fill = _read(source)

        assert fill.reports[0].report == BLOCK + round(BLOCK * HALF_RATE / DOCUMENT_RATE)


class TestClose:
    """A closed source ends its sound: every read after the close comes up empty."""

    def test_a_closed_source_reads_nothing(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)

        source.close()
        _, fill = _read(source)

        assert fill.frames == 0
        assert fill.reports == ()

    def test_an_open_source_reads_on(self) -> None:
        source = _source(ramp(LENGTH), sample_rate=DOCUMENT_RATE, output_rate=DOCUMENT_RATE, start=0)
        _read(source)

        _, fill = _read(source)

        assert fill.frames == BLOCK


class TestBegin:
    """Rule 5: a source begun on a stream plays at that stream's rate, from where it was asked to start."""

    def test_a_source_begun_at_another_rate_starts_where_it_was_asked_to(self) -> None:
        source = BufferSource(ramp(LENGTH), sample_rate=DOCUMENT_RATE, start=SEEK_TARGET)

        source.begin(FASTER_RATE, _unexpected)
        played, fill = _read(source)

        interior = np.arange(INTERIOR, BLOCK - INTERIOR)
        expected = SEEK_TARGET + interior * DOCUMENT_RATE / FASTER_RATE
        assert np.max(np.abs(_positions(played[interior]) - expected)) < PITCH_TOLERANCE
        assert fill.reports[0].report == SEEK_TARGET + round(BLOCK * DOCUMENT_RATE / FASTER_RATE)


class TestFill:
    def test_a_fill_shorter_than_its_block_ends_the_sound(self) -> None:
        block = np.zeros(BLOCK, dtype=np.float32)

        assert Fill(frames=BLOCK - 1, reports=()).ends(block)
        assert not Fill(frames=BLOCK, reports=()).ends(block)
