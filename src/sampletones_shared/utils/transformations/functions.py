import numpy as np

from sampletones_shared.types.array import ArrayOrNumeric


def identity(x: ArrayOrNumeric) -> ArrayOrNumeric:
    """
    Identity function.

    Args:
        x: Input value or array.

    Returns:
        Same as input.
    """
    return x


def energy(x: ArrayOrNumeric) -> ArrayOrNumeric:
    """
    Calculates the energy by squaring the absolute value.

    Args:
        x: Input value or array.

    Returns:
        Square of the absolute value of the input.
    """
    array: ArrayOrNumeric = np.square(np.abs(x))
    return array


def exp(x: ArrayOrNumeric) -> ArrayOrNumeric:
    """
    Exponential function.

    Args:
        x: Input value or array.

    Returns:
        ArrayOrScalar: Exponential of the input.
    """
    array: ArrayOrNumeric = np.exp(x)
    return array


def power(x: ArrayOrNumeric, a: float) -> ArrayOrNumeric:
    """
    Power function.

    Args:
        x: Input value or array.
        a: Power exponent.

    Returns:
        Input raised to the power of `a`.
    """
    array: ArrayOrNumeric = np.power(x, a)
    return array


def power_inverse(x: ArrayOrNumeric, a: float) -> ArrayOrNumeric:
    """
    Inverse power function.

    Args:
        x: Input value or array.
        a: Power exponent.

    Returns:
        Input raised to the power of `1 / a`.
    """
    array: ArrayOrNumeric = power(x, 1 / a)
    return array
