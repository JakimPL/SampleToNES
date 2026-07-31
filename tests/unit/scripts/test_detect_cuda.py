from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import pytest

from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.scripts import load_script

detect_cuda = load_script("scripts/detect_cuda.py")


def _completed(
    output: str,
    *,
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["nvidia-smi"], returncode=returncode, stdout=output, stderr="")


TABLE_OUTPUT_CUDA12 = (
    "Thu Jul 21 10:00:00 2026\n"
    "+-----------------------------------------------------------------------------+\n"
    "| NVIDIA-SMI 550.54.14   Driver Version: 550.54.14   CUDA Version: 12.4      |\n"
    "+-----------------------------------------------------------------------------+\n"
)
QUERY_OUTPUT_CUDA11 = "==============NVSMI LOG==============\n\nCUDA Version                          : 11.8\n"
NO_VERSION_OUTPUT = "GPU 0: NVIDIA GeForce RTX 4090 (UUID: GPU-abc)\n"


class TestSelectExtra(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        cuda_version: Optional[Tuple[int, int]]
        expected: Optional[str]

    test_cases = [
        TestCase(label="cuda_12_0_selects_gpu", cuda_version=(12, 0), expected="gpu"),
        TestCase(label="cuda_12_9_selects_gpu", cuda_version=(12, 9), expected="gpu"),
        TestCase(label="cuda_13_0_selects_gpu", cuda_version=(13, 0), expected="gpu"),
        TestCase(label="cuda_14_2_selects_gpu", cuda_version=(14, 2), expected="gpu"),
        TestCase(label="cuda_11_8_selects_legacy", cuda_version=(11, 8), expected="gpu-cuda11"),
        TestCase(label="cuda_11_0_selects_legacy", cuda_version=(11, 0), expected="gpu-cuda11"),
        TestCase(label="cuda_10_2_keeps_cpu", cuda_version=(10, 2), expected=None),
        TestCase(label="absent_version_keeps_cpu", cuda_version=None, expected=None),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_select_extra(self, test_case: "TestSelectExtra.TestCase") -> None:
        assert detect_cuda.select_extra(test_case.cuda_version) == test_case.expected


class TestQueryDriverCudaVersion(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        output: str
        expected: Optional[Tuple[int, int]]

    test_cases = [
        TestCase(label="table_header", output=TABLE_OUTPUT_CUDA12, expected=(12, 4)),
        TestCase(label="query_block", output=QUERY_OUTPUT_CUDA11, expected=(11, 8)),
        TestCase(label="cuda_13", output="CUDA Version: 13.0\n", expected=(13, 0)),
        TestCase(label="no_version_present", output=NO_VERSION_OUTPUT, expected=None),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_parse(self, test_case: "TestQueryDriverCudaVersion.TestCase", monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(command: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
            return _completed(test_case.output)

        monkeypatch.setattr(detect_cuda.subprocess, "run", fake_run)
        assert detect_cuda.query_driver_cuda_version(Path("nvidia-smi")) == test_case.expected

    def test_falls_back_to_query_flag(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(command: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
            output = QUERY_OUTPUT_CUDA11 if "-q" in command else NO_VERSION_OUTPUT
            return _completed(output)

        monkeypatch.setattr(detect_cuda.subprocess, "run", fake_run)
        assert detect_cuda.query_driver_cuda_version(Path("nvidia-smi")) == (11, 8)

    def test_missing_executable_keeps_cpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(command: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
            raise OSError("nvidia-smi is not executable")

        monkeypatch.setattr(detect_cuda.subprocess, "run", fake_run)
        assert detect_cuda.query_driver_cuda_version(Path("nvidia-smi")) is None

    def test_nonzero_return_code_keeps_cpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run(command: Sequence[str], **_: Any) -> subprocess.CompletedProcess[str]:
            return _completed(TABLE_OUTPUT_CUDA12, returncode=9)

        monkeypatch.setattr(detect_cuda.subprocess, "run", fake_run)
        assert detect_cuda.query_driver_cuda_version(Path("nvidia-smi")) is None


class TestFindNvidiaSmi:
    def test_uses_path_when_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(detect_cuda.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
        assert detect_cuda.find_nvidia_smi(system="Linux") == Path("/usr/bin/nvidia-smi")

    def test_absent_on_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(detect_cuda.shutil, "which", lambda name: None)
        assert detect_cuda.find_nvidia_smi(system="Linux") is None


class TestDetect:
    def test_macos_keeps_cpu(self) -> None:
        detection = detect_cuda.detect(system="Darwin")
        assert detection.extra is None
        assert detection.cuda_version is None

    def test_no_driver_keeps_cpu(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(detect_cuda.shutil, "which", lambda name: None)
        detection = detect_cuda.detect(system="Linux")
        assert detection.extra is None
        assert detection.nvidia_smi is None

    def test_selects_gpu_for_cuda12_driver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(detect_cuda.shutil, "which", lambda name: "/usr/bin/nvidia-smi")
        monkeypatch.setattr(detect_cuda.subprocess, "run", lambda command, **_: _completed(TABLE_OUTPUT_CUDA12))
        detection = detect_cuda.detect(system="Linux")
        assert detection.cuda_version == (12, 4)
        assert detection.extra == "gpu"
