from typing import Optional, Type, Union

CUPY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    import cupy as xp
    import cupy.typing as xp_typing

    CUPY_AVAILABLE = True  # pylint: disable=invalid-name
except (ImportError, ModuleNotFoundError):
    import warnings

    from sampletones.exceptions import CuPyNotInstalledWarning
    from sampletones.logger import logger

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
