from typing import Optional, Type, Union

import numpy as np

from sampletones_shared.logger import logger


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


CUPY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    _preload_cuda_libraries()
    import cupy as xp
    import cupy.typing as xp_typing

    CUPY_AVAILABLE = True  # pylint: disable=invalid-name,
    logger.info(f"CuPy {xp.__version__} is active")
except (AttributeError, ImportError, ModuleNotFoundError):
    import warnings

    from sampletones_shared.exceptions import CuPyNotInstalledWarning

    def _format_warning_no_location(
        message: Union[Warning, str],
        category: Type[Warning],
        filename: str,
        lineno: int,
        line: Optional[str] = None,
    ) -> str:
        return f"{category.__name__}: {message}\n"

    warnings.formatwarning = _format_warning_no_location
    warnings.warn("CuPy is not available, falling back to NumPy.", CuPyNotInstalledWarning)
    logger.warning("CuPy is not available, falling back to NumPy.")

    import numpy.typing as xp_typing  # pylint: disable=ungrouped-imports

    xp = np


def to_numpy(array: Union[np.ndarray, "xp.ndarray"]) -> np.ndarray:
    """Return a host NumPy array from the active backend.

    A NumPy array passes through; a CuPy array is copied from the device to the host. This is the
    single conversion point for handing backend arrays to NumPy-only code (spectra, histograms,
    serialization, tests), the mirror of ``xp.asarray`` which moves data onto the backend.
    """
    return xp.asnumpy(array) if CUPY_AVAILABLE else np.asarray(array)


__all__ = [
    "xp",
    "xp_typing",
    "CUPY_AVAILABLE",
    "to_numpy",
]
