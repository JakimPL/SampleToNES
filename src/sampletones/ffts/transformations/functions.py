import numpy as np
from scipy.special import gamma, gammaincc  # pylint: disable=no-name-in-module

ITERATIONS = 6


def zero(x: np.ndarray) -> np.ndarray:
    return np.zeros_like(x)


def identity(x: np.ndarray) -> np.ndarray:
    return x


def exp(x: np.ndarray) -> np.ndarray:
    return np.exp(x)


def expm1(x: np.ndarray) -> np.ndarray:
    return np.expm1(x)


def log1p(x: np.ndarray) -> np.ndarray:
    return np.log1p(x)


def general_interpolation(x: np.ndarray, a: float) -> np.ndarray:
    return np.exp(x) * gammaincc(a, x) - 1.0


def general_derivative(x: np.ndarray, a: float) -> np.ndarray:
    return np.exp(x) * gammaincc(a, x) - (x ** (a - 1)) / gamma(a)


def general_inverse(x: np.ndarray, a: float) -> np.ndarray:
    z = np.log1p(x)

    for _ in range(ITERATIONS):
        fx = general_interpolation(z, a) - x
        fpx = general_derivative(z, a)
        z -= fx / fpx

    return z
