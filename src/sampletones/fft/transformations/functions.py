import numpy as np

ITERATIONS = 6


def identity(x: np.ndarray) -> np.ndarray:
    """
    Identity function.

    Args:
        x (np.ndarray): Input array.

    Returns:
        np.ndarray: Same as input.
    """
    return x


def energy(x: np.ndarray) -> np.ndarray:
    """
    Calculates the energy of the FFT bins.

    Args:
        x (np.ndarray): Input array.

    Returns:
        np.ndarray: Energy of the FFT bins.
    """
    array: np.ndarray = np.square(np.abs(x))
    return array


def exp(x: np.ndarray) -> np.ndarray:
    """
    Exponential function.

    Args:
        x (np.ndarray): Input array.

    Returns:
        np.ndarray: Exponential of the input array.
    """
    array: np.ndarray = np.exp(x)
    return array


def power(x: np.ndarray, a: float) -> np.ndarray:
    """
    Power function.

    Args:
        x (np.ndarray): Input array.
        a (float): Power exponent.

    Returns:
        np.ndarray: Input array raised to the power of `a`.
    """
    array: np.ndarray = np.power(x, a)
    return array


def power_inverse(x: np.ndarray, a: float) -> np.ndarray:
    """
    Inverse power function.

    Args:
        x (np.ndarray): Input array.
        a (float): Power exponent.

    Returns:
        np.ndarray: Input array raised to the power of `1 / a`.
    """
    array: np.ndarray = power(x, 1 / a)
    return array
