from typing import Optional, Type, Union


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

    CUPY_AVAILABLE = True  # pylint: disable=invalid-name
except (AttributeError, ImportError, ModuleNotFoundError):
    import warnings

    from sampletones_shared.exceptions import CuPyNotInstalledWarning
    from sampletones_shared.logger import logger

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

    import numpy as xp
    import numpy.typing as xp_typing

__all__ = [
    "xp",
    "xp_typing",
    "CUPY_AVAILABLE",
]
