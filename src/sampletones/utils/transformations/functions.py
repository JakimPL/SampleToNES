import numpy as np

from sampletones.types.array import ArrayOrScalar


def identity(x: ArrayOrScalar) -> ArrayOrScalar:
    """
    Identity function.

    Args:
        x: Input value or array.

    Returns:
        Same as input.
    """
    return x


def energy(x: ArrayOrScalar) -> ArrayOrScalar:
    """
    Calculates the energy by squaring the absolute value.

    Args:
        x: Input value or array.

    Returns:
        Square of the absolute value of the input.
    """
    array: ArrayOrScalar = np.square(np.abs(x))
    return array


def exp(x: ArrayOrScalar) -> ArrayOrScalar:
    """
    Exponential function.

    Args:
        x: Input value or array.

    Returns:
        ArrayOrScalar: Exponential of the input.
    """
    array: ArrayOrScalar = np.exp(x)
    return array


def power(x: ArrayOrScalar, a: float) -> ArrayOrScalar:
    """
    Power function.

    Args:
        x: Input value or array.
        a: Power exponent.

    Returns:
        Input raised to the power of `a`.
    """
    array: ArrayOrScalar = np.power(x, a)
    return array


def power_inverse(x: ArrayOrScalar, a: float) -> ArrayOrScalar:
    """
    Inverse power function.

    Args:
        x: Input value or array.
        a: Power exponent.

    Returns:
        Input raised to the power of `1 / a`.
    """
    array: ArrayOrScalar = power(x, 1 / a)
    return array
