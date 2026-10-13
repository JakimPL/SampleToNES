import warnings
from typing import Any, Final, Optional, Tuple, Type, Union

import numpy as np

from sampletones_shared.exceptions import CuPyUnavailableWarning, GPUBackendError
from sampletones_shared.logger import logger

CUPY_MISSING_MESSAGE: Final[str] = "CuPy is not available, falling back to NumPy."
NO_DEVICE_MESSAGE: Final[str] = "CuPy finds no graphics card to compute on ({reason}), falling back to NumPy."
NO_DEVICE_COUNTED: Final[str] = "the driver counts no device"
MINIMUM_DEVICES: Final[int] = 1
CUPY_BACKEND: Final[str] = "CuPy"
NUMPY_BACKEND: Final[str] = "NumPy"
GPU_PROBE_SIZE: Final[int] = 64
GPU_PROBE_MISMATCH: Final[str] = "The graphics card answered {device}, while the CPU answered {host}."


def _preload_cuda_libraries() -> None:
    """Make CUDA libraries shipped as ``nvidia-*-cu12`` wheels discoverable by CuPy.

    CuPy loads CUDA shared objects (e.g. ``libnvrtc.so.12``) by soname through the
    system dynamic loader, which does not search ``site-packages``. When the libraries
    come from the pip wheels (the ``gpu`` extra), preload them with ``RTLD_GLOBAL`` so
    CuPy's later ``dlopen`` calls resolve against the already-loaded handles.

    No-op when the wheels are absent (system CUDA, Windows, or the NumPy fallback).
    """
    import ctypes
    import glob
    import os

    try:
        import nvidia
    except ImportError:
        return

    for base in list(getattr(nvidia, "__path__", [])):
        for library in sorted(glob.glob(os.path.join(base, "*", "lib", "lib*.so.*"))):
            try:
                ctypes.CDLL(library, mode=ctypes.RTLD_GLOBAL)
            except OSError:
                pass


def _format_warning_no_location(
    message: Union[Warning, str],
    category: Type[Warning],
    filename: str,  # pylint: disable=unused-argument
    lineno: int,  # pylint: disable=unused-argument
    line: Optional[str] = None,  # pylint: disable=unused-argument
) -> str:
    return f"{category.__name__}: {message}\n"


def _absent_device_reason(cupy: Any) -> Optional[str]:
    """Why CuPy has no graphics card to compute on, or ``None`` once the driver counts one.

    Importing CuPy loads its libraries, and the driver is first asked when a computation starts.
    Asking for the device count while the backend is chosen settles a machine without a card, or
    without a working driver, on NumPy before anything is computed.

    Args:
        cupy: The imported CuPy module.

    Returns:
        Optional[str]: The reason the process falls back to NumPy, or ``None`` where a card answers.
    """
    try:
        count = cupy.cuda.runtime.getDeviceCount()
    except cupy.cuda.runtime.CUDARuntimeError as error:
        return NO_DEVICE_MESSAGE.format(reason=error)

    if count < MINIMUM_DEVICES:
        return NO_DEVICE_MESSAGE.format(reason=NO_DEVICE_COUNTED)

    return None


FALLBACK_REASON: Optional[str]
try:
    _preload_cuda_libraries()
    import cupy as xp
    import cupy.typing as xp_typing
except (AttributeError, ImportError):
    FALLBACK_REASON = CUPY_MISSING_MESSAGE
else:
    FALLBACK_REASON = _absent_device_reason(xp)

if FALLBACK_REASON is not None:
    import numpy.typing as xp_typing  # pylint: disable=ungrouped-imports

    xp = np

CUPY_AVAILABLE = FALLBACK_REASON is None


def describe_array_backend() -> str:
    """The array backend the process computes on, named with its version."""
    name = CUPY_BACKEND if CUPY_AVAILABLE else NUMPY_BACKEND
    return f"{name} {xp.__version__}"


def _probe_sums(module: Any) -> Tuple[float, float]:
    """The sum of squares and the summed outer product of the first probe-size integers, computed by ``module``.

    Both sums stay below 2**24 at the probe size, so single precision carries them exactly in any
    order of summation and the card's answer is held to the CPU's as an equality.
    """
    values = module.arange(GPU_PROBE_SIZE, dtype=module.float32)
    return float((values * values).sum()), float((values[:, None] @ values[None, :]).sum())


def exercise_gpu() -> str:
    """Computes on the graphics card, holds its answer to the CPU's, and names the device.

    A kernel is compiled for the elementwise product, and the matrix product goes through cuBLAS,
    so a build missing the CUDA libraries or the headers the compiler reads fails here rather than
    in a conversion.

    Returns:
        str: The backend and the device's name.

    Raises:
        GPUBackendError: If the process computes on the CPU, or the card's answer differs from the CPU's.
    """
    if FALLBACK_REASON is not None:
        raise GPUBackendError(FALLBACK_REASON)

    device = _probe_sums(xp)
    host = _probe_sums(np)
    if device != host:
        raise GPUBackendError(GPU_PROBE_MISMATCH.format(device=device, host=host))

    properties = xp.cuda.runtime.getDeviceProperties(xp.cuda.runtime.getDevice())
    return f"{describe_array_backend()} on {properties['name'].decode()}"


def report_array_backend() -> None:
    """States which array backend the process computes on.

    Choosing the backend is an import, and an import runs before an entry point has read the
    verbosity it was configured with. Announcing it separately puts the line where a reader is —
    a run of the application, or a reconstruction from the command line — and leaves a tool that
    imports the array vocabulary for its types alone to its own output.
    """
    if FALLBACK_REASON is None:
        logger.info(f"{describe_array_backend()} is active")
        return

    warnings.formatwarning = _format_warning_no_location
    warnings.warn(FALLBACK_REASON, CuPyUnavailableWarning)
    logger.warning(FALLBACK_REASON)


def to_numpy(array: Union[np.ndarray, "xp.ndarray"]) -> np.ndarray:
    """Return a host NumPy array from the active backend.

    A NumPy array passes through; a CuPy array is copied from the device to the host. This is the
    single conversion point for handing backend arrays to NumPy-only code (spectra, histograms,
    serialization, tests), the mirror of ``xp.asarray`` which moves data onto the backend.
    """
    return xp.asnumpy(array) if CUPY_AVAILABLE else np.asarray(array)


__all__ = [
    "CUPY_AVAILABLE",
    "FALLBACK_REASON",
    "describe_array_backend",
    "exercise_gpu",
    "report_array_backend",
    "to_numpy",
    "xp",
    "xp_typing",
]
