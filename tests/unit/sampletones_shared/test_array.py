import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Optional

import numpy as np
import pytest

from sampletones_shared import array
from sampletones_shared.array import CUPY_AVAILABLE, describe_array_backend, exercise_gpu, xp
from sampletones_shared.exceptions import GPUBackendError
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

CUPY_REQUIRED_REASON = "the GPU backend needs CuPy and an NVIDIA graphics card"
CUPY_INSTALLED_REASON = "the fallback is chosen over an installed CuPy"
FALLBACK_ENDING = "falling back to NumPy."
HIDDEN_DEVICES = {"CUDA_VISIBLE_DEVICES": ""}
BACKEND_REPORT = "from sampletones_shared import array; print(array.CUPY_AVAILABLE, array.describe_array_backend())"


class FakeCUDARuntimeError(Exception):
    pass


def _fake_cupy(count: Optional[int], error: Optional[str]) -> SimpleNamespace:
    """A CuPy whose runtime counts ``count`` devices, or raises ``error`` when one is given."""

    def get_device_count() -> int:
        if error is not None:
            raise FakeCUDARuntimeError(error)

        assert count is not None
        return count

    runtime = SimpleNamespace(getDeviceCount=get_device_count, CUDARuntimeError=FakeCUDARuntimeError)
    return SimpleNamespace(cuda=SimpleNamespace(runtime=runtime))


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
        monkeypatch.setattr(array, "FALLBACK_REASON", array.CUPY_MISSING_MESSAGE)

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


class TestAbsentDeviceReason(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Optional[str]
        count: Optional[int]
        error: Optional[str]

    test_cases = (
        TestCase(count=1, error=None, expected=None, label="a_card_answers"),
        TestCase(count=0, error=None, expected=array.NO_DEVICE_COUNTED, label="the_driver_counts_none"),
        TestCase(
            count=None,
            error="cudaErrorNoDevice: no CUDA-capable device is detected",
            expected="cudaErrorNoDevice: no CUDA-capable device is detected",
            label="the_runtime_finds_no_device",
        ),
        TestCase(
            count=None,
            error="cudaErrorInsufficientDriver: CUDA driver version is insufficient",
            expected="cudaErrorInsufficientDriver",
            label="the_driver_is_too_old",
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_a_missing_card_names_the_fallback(self, test_case: TestCase) -> None:
        reason = array._absent_device_reason(  # pylint: disable=protected-access
            _fake_cupy(test_case.count, test_case.error)
        )

        if test_case.expected is None:
            assert reason is None
            return

        assert reason is not None
        assert test_case.expected in reason
        assert reason.endswith(FALLBACK_ENDING)


class TestBackendSelection:
    @pytest.mark.skipif(importlib.util.find_spec("cupy") is None, reason=CUPY_INSTALLED_REASON)
    def test_a_process_seeing_no_card_computes_on_numpy(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-c", BACKEND_REPORT],
            env={**os.environ, **HIDDEN_DEVICES},
            capture_output=True,
            text=True,
            check=True,
        )

        assert completed.stdout.split() == ["False", array.NUMPY_BACKEND, np.__version__]
