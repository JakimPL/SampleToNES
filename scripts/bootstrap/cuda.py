import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Mapping, Optional, Sequence, Tuple

from bootstrap.platforms.protocol import Platform
from bootstrap.project import GPU_CUDA11_EXTRA, GPU_EXTRA

NVIDIA_SMI: Final[str] = "nvidia-smi"
CUDA12_MAJOR: Final[int] = 12
CUDA11_MAJOR: Final[int] = 11
CUDA_VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(r"CUDA Version\s*:?\s*(\d+)\.(\d+)")
QUERY_ARGUMENTS: Final[Tuple[Tuple[str, ...], ...]] = ((), ("-q",))


@dataclass(frozen=True, kw_only=True)
class CudaDetection:
    """The CuPy extra the host's NVIDIA driver maps to, and what was found to choose it.

    Attributes:
        extra: The optional-dependency extra matching the driver, or ``None`` for the CPU backend.
        reason: One line saying what was found and what it selects.
    """

    extra: Optional[str]
    reason: str


def find_nvidia_smi(platform: Platform, environment: Mapping[str, str]) -> Optional[Path]:
    """The driver's ``nvidia-smi``: on ``PATH``, or at a location the system's driver installs it.

    Args:
        platform: The system, which names the locations off ``PATH``.
        environment: The variables those locations are read from.

    Returns:
        Optional[Path]: The executable, or ``None`` where no NVIDIA driver is installed.
    """
    located = shutil.which(NVIDIA_SMI)
    if located is not None:
        return Path(located)

    return next((candidate for candidate in platform.nvidia_smi_locations(environment) if candidate.exists()), None)


def _run_nvidia_smi(nvidia_smi: Path, arguments: Sequence[str]) -> Optional[str]:
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
    """The newest CUDA version the driver supports, as ``(major, minor)``.

    ``nvidia-smi`` reports the driver's newest supported CUDA version, which governs CuPy wheel
    selection: CuPy wheels bind to the driver, whatever CUDA Toolkit the system carries. The
    default table carries the value, and ``-q`` provides a structured fallback for formats that
    omit it.
    """
    for arguments in QUERY_ARGUMENTS:
        output = _run_nvidia_smi(nvidia_smi, arguments)
        if output is None:
            continue

        match = CUDA_VERSION_PATTERN.search(output)
        if match is not None:
            return int(match.group(1)), int(match.group(2))

    return None


def select_extra(cuda_version: Optional[Tuple[int, int]]) -> Optional[str]:
    """The optional-dependency extra matching a driver's CUDA version.

    CUDA 12 and newer drivers map to the ``gpu`` extra (``cupy-cuda12x``): a CUDA 12 wheel runs on
    every 12.x driver through Enhanced Compatibility and on newer drivers through backward
    compatibility. CUDA 11 drivers map to the legacy ``gpu-cuda11`` extra. Older drivers map to
    ``None``, keeping the CPU backend.
    """
    if cuda_version is None:
        return None

    major = cuda_version[0]
    if major >= CUDA12_MAJOR:
        return GPU_EXTRA

    if major == CUDA11_MAJOR:
        return GPU_CUDA11_EXTRA

    return None


def _describe(*, cuda_version: Optional[Tuple[int, int]], extra: Optional[str]) -> str:
    if cuda_version is None:
        return "NVIDIA driver detected, though its CUDA version was unreadable; keeping the CPU (NumPy) backend."

    major, minor = cuda_version
    if extra is None:
        return (
            f"Detected CUDA {major}.{minor}, which predates the supported CuPy builds; "
            "keeping the CPU (NumPy) backend."
        )

    return f"Detected an NVIDIA driver supporting CUDA {major}.{minor}; selecting the '{extra}' extra."


def detect(platform: Platform, environment: Mapping[str, str]) -> CudaDetection:
    """The CUDA capability of the host and the CuPy extra that matches it.

    Args:
        platform: The system the detection runs on.
        environment: The variables the driver's locations are read from.

    Returns:
        CudaDetection: What was found and the extra it selects.
    """
    if platform.cpu_backend_reason is not None:
        return CudaDetection(extra=None, reason=platform.cpu_backend_reason)

    nvidia_smi = find_nvidia_smi(platform, environment)
    if nvidia_smi is None:
        return CudaDetection(
            extra=None,
            reason="No NVIDIA driver detected (nvidia-smi is absent); keeping the CPU (NumPy) backend.",
        )

    cuda_version = query_driver_cuda_version(nvidia_smi)
    extra = select_extra(cuda_version)
    return CudaDetection(extra=extra, reason=_describe(cuda_version=cuda_version, extra=extra))
