import numpy as np


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
