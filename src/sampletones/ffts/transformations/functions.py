import numpy as np
from scipy.special import gamma, gammaincc  # pylint: disable=no-name-in-module

ITERATIONS = 6


def zero(x: np.ndarray) -> np.ndarray:
    return np.zeros_like(x)


def identity(x: np.ndarray) -> np.ndarray:
    return x


def exp(x: np.ndarray) -> np.ndarray:
    array: np.ndarray = np.exp(x)
    return array


def expm1(x: np.ndarray) -> np.ndarray:
    array: np.ndarray = np.expm1(x)
    return array


def log1p(x: np.ndarray) -> np.ndarray:
    array: np.ndarray = np.log1p(x)
    return array


def general_interpolation(x: np.ndarray, a: float) -> np.ndarray:
    array: np.ndarray = np.exp(x) * gammaincc(a, x) - 1.0
    return array


def general_derivative(x: np.ndarray, a: float) -> np.ndarray:
    array: np.ndarray = np.exp(x) * gammaincc(a, x) - (x ** (a - 1)) / gamma(a)
    return array


def general_inverse(x: np.ndarray, a: float) -> np.ndarray:
    z: np.ndarray = np.log1p(x)

    for _ in range(ITERATIONS):
        fx = general_interpolation(z, a) - x
        fpx = general_derivative(z, a)
        z -= fx / fpx

    return z
