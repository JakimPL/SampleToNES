import gc
from typing import Final

import numpy as np

from sampletones_application.ui.elements.graphs.layers.decimation import KEPT_DECIMATIONS, Decimations
from sampletones_core.audio import minmax_decimate

MAX_POINTS: Final[int] = 8
LONG: Final[int] = 64
SHORT: Final[int] = 4


def _waveform(length: int, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).standard_normal(length).astype(np.float32)


class TestThePointsAnArrayDrawsAs:
    def test_a_long_array_reduces_to_its_extremes_per_bucket(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(LONG, 0)

        positions, values = decimations.points(audio)

        expected_positions, expected_values = minmax_decimate(audio, num_buckets=MAX_POINTS)
        np.testing.assert_array_equal(positions, expected_positions)
        np.testing.assert_array_equal(values, expected_values)

    def test_a_short_array_draws_every_sample(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(SHORT, 0)

        positions, values = decimations.points(audio)

        np.testing.assert_array_equal(positions, np.arange(SHORT, dtype=np.float32))
        np.testing.assert_array_equal(values, audio)

    def test_the_peak_is_the_arrays_own(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(LONG, 1)

        assert decimations.peak(audio) == float(np.max(np.abs(audio)))


class TestWhatTheMemoKeeps:
    """A reduction is made once per array and read back by identity, and goes with the array."""

    def test_a_second_showing_reads_the_same_points(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(LONG, 0)

        first = decimations.points(audio)
        second = decimations.points(audio)

        assert second[0] is first[0]
        assert second[1] is first[1]

    def test_an_equal_array_of_its_own_is_reduced_apart(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(LONG, 0)
        twin = audio.copy()

        assert decimations.points(twin)[1] is not decimations.points(audio)[1]

    def test_a_collected_array_takes_its_points_with_it(self) -> None:
        decimations = Decimations(MAX_POINTS)
        audio = _waveform(LONG, 0)
        identity = id(audio)
        decimations.points(audio)

        del audio
        gc.collect()

        assert identity not in decimations._points

    def test_the_reductions_read_longest_ago_go_first(self) -> None:
        decimations = Decimations(MAX_POINTS)
        kept = [_waveform(LONG, seed) for seed in range(KEPT_DECIMATIONS + 1)]

        for audio in kept:
            decimations.points(audio)

        assert id(kept[0]) not in decimations._points
        assert all(id(audio) in decimations._points for audio in kept[1:])
