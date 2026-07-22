import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional, Sequence, Tuple

NVIDIA_SMI: Final[str] = "nvidia-smi"

DARWIN: Final[str] = "Darwin"
WINDOWS: Final[str] = "Windows"

EXTRA_GPU: Final[str] = "gpu"
EXTRA_GPU_CUDA11: Final[str] = "gpu-cuda11"

CUDA12_MAJOR: Final[int] = 12
CUDA11_MAJOR: Final[int] = 11

CUDA_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(r"CUDA Version\s*:?\s*(\d+)\.(\d+)")

WINDOWS_NVIDIA_SMI_SUBPATHS: Final[Sequence[Tuple[str, str]]] = (
    ("SystemRoot", "System32/nvidia-smi.exe"),
    ("ProgramFiles", "NVIDIA Corporation/NVSMI/nvidia-smi.exe"),
)


@dataclass(frozen=True, kw_only=True)
class CudaDetection:
    """The NVIDIA driver capability observed on the host and the CuPy extra it maps to."""

    system: str
    nvidia_smi: Optional[Path]
    cuda_version: Optional[Tuple[int, int]]
    extra: Optional[str]
    reason: str


def _windows_nvidia_smi_candidates() -> List[Path]:
    """Return the fixed Windows locations where the driver installs ``nvidia-smi.exe``."""
    candidates: List[Path] = []
    for variable, relative in WINDOWS_NVIDIA_SMI_SUBPATHS:
        root = os.environ.get(variable)
        if root:
            candidates.append(Path(root) / relative)

    return candidates


def find_nvidia_smi(*, system: str) -> Optional[Path]:
    """Return the path to ``nvidia-smi`` when an NVIDIA driver is installed.

    ``nvidia-smi`` ships with the driver and lands on ``PATH`` on Linux and Windows. On Windows
    it may also sit in a fixed system location off ``PATH``, so probe those as a fallback.
    """
    located = shutil.which(NVIDIA_SMI)
    if located is not None:
        return Path(located)

    if system == WINDOWS:
        for candidate in _windows_nvidia_smi_candidates():
            if candidate.exists():
                return candidate
    return None


def _run_nvidia_smi(
    nvidia_smi: Path,
    arguments: Sequence[str],
) -> Optional[str]:
    """Return the combined output of an ``nvidia-smi`` invocation that succeeds."""
    try:
        completed = subprocess.run(
            [str(nvidia_smi), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    return completed.stdout + completed.stderr


def query_driver_cuda_version(nvidia_smi: Path) -> Optional[Tuple[int, int]]:
    """Return the maximum CUDA version the driver supports, as ``(major, minor)``.

    ``nvidia-smi`` reports the driver's maximum supported CUDA version, which governs CuPy wheel
    selection: CuPy wheels bind to the driver rather than to a system CUDA Toolkit. The default
    table carries the value, and ``-q`` provides a structured fallback for formats that omit it.
    """
    for arguments in ((), ("-q",)):
        output = _run_nvidia_smi(nvidia_smi, arguments)
        if output is None:
            continue
        match = CUDA_VERSION_PATTERN.search(output)
        if match is not None:
            return int(match.group(1)), int(match.group(2))

    return None


def select_extra(cuda_version: Optional[Tuple[int, int]]) -> Optional[str]:
    """Return the optional-dependency extra matching a driver's CUDA version.

    CUDA 12 and newer drivers map to the ``gpu`` extra (``cupy-cuda12x``): a CUDA 12 wheel runs on
    every 12.x driver through Enhanced Compatibility and on newer drivers through backward
    compatibility. CUDA 11 drivers map to the legacy ``gpu-cuda11`` extra. Older drivers map to
    ``None``, keeping the CPU backend.
    """
    if cuda_version is None:
        return None

    major = cuda_version[0]
    if major >= CUDA12_MAJOR:
        return EXTRA_GPU

    if major == CUDA11_MAJOR:
        return EXTRA_GPU_CUDA11

    return None


def _describe(
    *,
    cuda_version: Optional[Tuple[int, int]],
    extra: Optional[str],
) -> str:
    """Return a one-line summary of a driver-present detection outcome."""
    if cuda_version is None:
        return "NVIDIA driver detected, though its CUDA version was unreadable; keeping the CPU (NumPy) backend."
    major, minor = cuda_version
    if extra is None:
        return (
            f"Detected CUDA {major}.{minor}, which predates the supported CuPy builds; "
            "keeping the CPU (NumPy) backend."
        )
    return f"Detected an NVIDIA driver supporting CUDA {major}.{minor}; selecting the '{extra}' extra."


def detect(*, system: str) -> CudaDetection:
    """Return the CUDA capability of the host and the CuPy extra that matches it.

    macOS keeps the CPU backend, since NVIDIA CUDA is available only on Linux and Windows. On
    those systems the driver's ``nvidia-smi`` supplies the CUDA version that drives selection.
    """
    if system == DARWIN:
        return CudaDetection(
            system=system,
            nvidia_smi=None,
            cuda_version=None,
            extra=None,
            reason="NVIDIA CUDA is available on Linux and Windows; on macOS, keeping the CPU (NumPy) backend.",
        )

    nvidia_smi = find_nvidia_smi(system=system)
    if nvidia_smi is None:
        return CudaDetection(
            system=system,
            nvidia_smi=None,
            cuda_version=None,
            extra=None,
            reason="No NVIDIA driver detected (nvidia-smi is absent); keeping the CPU (NumPy) backend.",
        )

    cuda_version = query_driver_cuda_version(nvidia_smi)
    extra = select_extra(cuda_version)
    return CudaDetection(
        system=system,
        nvidia_smi=nvidia_smi,
        cuda_version=cuda_version,
        extra=extra,
        reason=_describe(cuda_version=cuda_version, extra=extra),
    )


def _format_version(cuda_version: Optional[Tuple[int, int]]) -> str:
    """Return a human-readable CUDA version, or ``unknown`` when it was unreadable."""
    if cuda_version is None:
        return "unknown"

    major, minor = cuda_version
    return f"{major}.{minor}"


def _print_report(detection: CudaDetection) -> None:
    """Print the full detection outcome to stdout for a human reader."""
    nvidia_smi = str(detection.nvidia_smi) if detection.nvidia_smi is not None else "not found"
    extra = detection.extra if detection.extra is not None else "none (CPU)"
    lines = [
        f"System:         {detection.system}",
        f"nvidia-smi:     {nvidia_smi}",
        f"Driver CUDA:    {_format_version(detection.cuda_version)}",
        f"Selected extra: {extra}",
        f"Summary:        {detection.reason}",
    ]
    print("\n".join(lines))


def main(argv: Sequence[str]) -> int:
    """Report the detected CUDA capability, or print the matching extra for install scripts.

    Under ``--extra`` the chosen extra name is written to stdout (empty when the CPU backend is
    kept) so a Makefile can capture it, and the summary is written to stderr. Without it, a full
    report is written to stdout.
    """
    parser = argparse.ArgumentParser(
        description="Select the CuPy extra matching the local NVIDIA driver.",
    )
    parser.add_argument(
        "--extra",
        action="store_true",
        help="print the chosen optional-dependency extra to stdout (empty when the CPU backend is kept)",
    )
    arguments = parser.parse_args(list(argv))
    detection = detect(system=platform.system())

    if arguments.extra:
        print(detection.reason, file=sys.stderr)
        if detection.extra is not None:
            print(detection.extra)
    else:
        _print_report(detection)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
