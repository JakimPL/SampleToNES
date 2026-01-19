from typing import Iterable, Optional

import numpy as np

from sampletones.constants.audio import BUFFER_SIZES, SAMPLE_RATES


def validate_audio_array(
    audio: np.ndarray,
    allowed_dims: Optional[Iterable[int]] = (1,),
) -> None:
    """
    Validate that input is a numpy array with allowed dimensions.
    Expects 1D array by default.

    Args:
        audio: Array to validate.
        allowed_dims: Iterable of allowed number of dimensions.
            If None, any number of dimensions is allowed.

    Raises:
        TypeError: If audio is not a numpy array.
        ValueError: If audio is not one of the allowed dimensions.
    """
    if not isinstance(audio, np.ndarray):
        raise TypeError(f"Expected audio to be np.ndarray, got {type(audio)}")

    if not np.issubdtype(audio.dtype, np.number):
        raise TypeError(f"Expected audio array to have numeric dtype, got {audio.dtype}")

    if allowed_dims is not None and audio.ndim not in allowed_dims:
        dims = "D, ".join(str(dim) for dim in allowed_dims)
        if not dims:
            raise ValueError("No allowed dimensions specified for audio array validation")

        raise ValueError(f"Expected audio to be: {dims}D, got {audio.ndim}D array")


def validate_sample_rate(sample_rate: int) -> None:
    """
    Validate that sample rate is an allowed value.

    Args:
        sample_rate: Sample rate in Hz to validate.

    Raises:
        TypeError: If sample_rate is not an integer.
        ValueError: If sample_rate is not in allowed sample rates.
    """
    if not isinstance(sample_rate, int):
        raise TypeError(f"sample_rate must be an integer, got {type(sample_rate)}")

    if sample_rate not in SAMPLE_RATES:
        allowed_rates = ", ".join(str(rate) for rate in SAMPLE_RATES)
        raise ValueError(f"sample_rate must be one of [{allowed_rates}], got {sample_rate}")


def validate_buffer_size(buffer_size: int) -> None:
    """
    Validate that buffer size is an allowed value.

    Args:
        buffer_size: Buffer size in samples to validate.

    Raises:
        TypeError: If buffer_size is not an integer.
        ValueError: If buffer_size is not in allowed buffer sizes.
    """
    if not isinstance(buffer_size, int):
        raise TypeError(f"buffer_size must be an integer, got {type(buffer_size)}")

    if buffer_size not in BUFFER_SIZES:
        allowed_sizes = ", ".join(str(size) for size in BUFFER_SIZES)
        raise ValueError(f"buffer_size must be one of [{allowed_sizes}], got {buffer_size}")
