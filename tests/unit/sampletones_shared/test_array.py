import numpy as np
import pytest

from sampletones_shared import array
from sampletones_shared.array import CUPY_AVAILABLE, describe_array_backend, exercise_gpu, xp
from sampletones_shared.exceptions import GPUBackendError

CUPY_REQUIRED_REASON = "the GPU backend needs CuPy and an NVIDIA graphics card"


class TestDescribeArrayBackend:
    def test_the_backend_is_named_with_its_version(self) -> None:
        description = describe_array_backend()

        assert description.endswith(xp.__version__)
        assert description.startswith(array.CUPY_BACKEND if CUPY_AVAILABLE else array.NUMPY_BACKEND)

    def test_the_cpu_backend_is_numpy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(array, "CUPY_AVAILABLE", False)

        assert describe_array_backend().startswith(array.NUMPY_BACKEND)


class TestExerciseGpu:
    def test_a_cpu_build_is_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(array, "CUPY_AVAILABLE", False)

        with pytest.raises(GPUBackendError, match="falling back to NumPy"):
            exercise_gpu()

    def test_the_probe_sums_are_exact_in_single_precision(self) -> None:
        squares, products = array._probe_sums(np)  # pylint: disable=protected-access

        assert squares == sum(value * value for value in range(array.GPU_PROBE_SIZE))
        assert products == sum(range(array.GPU_PROBE_SIZE)) ** 2
        assert max(squares, products) < 2**24

    @pytest.mark.skipif(not CUPY_AVAILABLE, reason=CUPY_REQUIRED_REASON)
    def test_the_card_answers_and_is_named(self) -> None:
        description = exercise_gpu()

        assert description.startswith(describe_array_backend())
        assert " on " in description
