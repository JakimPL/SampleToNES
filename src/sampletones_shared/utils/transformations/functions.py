import numpy as np

from sampletones_shared.types.array import ArrayOrNumeric


def identity(x: ArrayOrNumeric) -> ArrayOrNumeric:
    """
    Returns the argument unchanged, serving as the no-op transformation.

    Args:
        x: Input value or array.

    Returns:
        The input, unchanged.
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
    Computes the element-wise natural exponential `e^x`.

    Args:
        x: Input value or array.

    Returns:
        Exponential of the input.
    """
    array: ArrayOrNumeric = np.exp(x)
    return array


def power(x: ArrayOrNumeric, a: float) -> ArrayOrNumeric:
    """
    Raises the input to the power `a` (`x^a`).

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
    Raises the input to the reciprocal power `1 / a` (`x^(1/a)`), inverting `power`.

    Args:
        x: Input value or array.
        a: Power exponent.

    Returns:
        Input raised to the power of `1 / a`.
    """
    array: ArrayOrNumeric = power(x, 1 / a)
    return array


def yeo_johnson(
    x: ArrayOrNumeric,
    *,
    exponent: float,
    epsilon: float,
) -> ArrayOrNumeric:
    """
    Yeo-Johnson forward transformation for non-negative inputs.

    Computes `((x + epsilon)^exponent - epsilon^exponent) / exponent`.

    At `exponent = 1` this reduces to the identity. As `exponent → 0` this approaches
    `log(1 + x / epsilon)`. The `epsilon` shift keeps the transform real at `x = 0`
    and defines the knee between the linear and logarithmic regimes.

    Args:
        x: Input value or array (must be non-negative).
        exponent: Shape parameter λ ∈ (0, 1].
        epsilon: Noise floor defining the linear-to-log transition point.

    Returns:
        Transformed value or array.
    """
    array: ArrayOrNumeric = (np.power(x + epsilon, exponent) - epsilon**exponent) / exponent
    return array


def yeo_johnson_inverse(
    y: ArrayOrNumeric,
    *,
    exponent: float,
    epsilon: float,
) -> ArrayOrNumeric:
    """
    Inverse of the Yeo-Johnson forward transformation for non-negative inputs.

    Computes `(exponent * y + epsilon^exponent)^(1 / exponent) - epsilon`.

    Args:
        y: Transformed value or array.
        exponent: Shape parameter λ ∈ (0, 1].
        epsilon: Noise floor used in the forward transformation.

    Returns:
        Recovered original value or array.
    """
    array: ArrayOrNumeric = np.power(exponent * y + epsilon**exponent, 1.0 / exponent) - epsilon
    return array


def yeo_johnson_log(
    x: ArrayOrNumeric,
    *,
    epsilon: float,
) -> ArrayOrNumeric:
    """
    Limiting case of the Yeo-Johnson transform as `power → 0`.

    Computes `log(1 + x / epsilon)`, the natural logarithm normalized by the
    noise floor. Uses `np.log1p` for numerical stability near `x = 0`.

    Args:
        x: Input value or array (must be non-negative).
        epsilon: Noise floor defining the reference level for the log scale.

    Returns:
        Log-transformed value or array.
    """
    array: ArrayOrNumeric = np.log1p(x / epsilon)
    return array


def yeo_johnson_log_inverse(
    y: ArrayOrNumeric,
    *,
    epsilon: float,
) -> ArrayOrNumeric:
    """
    Inverse of the Yeo-Johnson log transformation (limit as `power → 0`).

    Computes `epsilon * (e^y - 1)`. Uses `np.expm1` for numerical stability near `y = 0`.

    Args:
        y: Log-transformed value or array.
        epsilon: Noise floor used in the forward log transformation.

    Returns:
        Recovered original value or array.
    """
    array: ArrayOrNumeric = epsilon * np.expm1(y)
    return array
