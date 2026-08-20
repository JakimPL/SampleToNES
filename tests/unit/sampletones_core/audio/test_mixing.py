import numpy as np
import pytest

from sampletones_core.audio.mixing import mix_audios


class TestMixAudios:
    def test_pads_shorter_recordings_to_the_longest(self) -> None:
        mixed = mix_audios(
            [
                np.array([1.0, 2.0, 3.0], dtype=np.float64),
                np.array([4.0], dtype=np.float64),
            ]
        )

        np.testing.assert_array_equal(mixed, np.array([5.0, 2.0, 3.0]))

    def test_sums_equal_length_recordings(self) -> None:
        mixed = mix_audios(
            [
                np.array([1.0, 1.0], dtype=np.float64),
                np.array([2.0, 2.0], dtype=np.float64),
            ]
        )

        np.testing.assert_array_equal(mixed, np.array([3.0, 3.0]))

    def test_a_single_recording_is_the_mix_itself(self) -> None:
        recording = np.array([1.0, 2.0], dtype=np.float64)

        mixed = mix_audios([recording])

        assert mixed is recording

    def test_empty_recordings_raise(self) -> None:
        with pytest.raises(ValueError, match="At least one recording"):
            mix_audios([])
