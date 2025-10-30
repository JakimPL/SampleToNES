from dataclasses import dataclass, field
from typing import NamedTuple

import numpy as np
from scipy.special import gamma, gammaincc

from typehints.general import BinaryTransformation, UnaryTransformation
from utils.functions import exp, expm1, identity, log1p, zero

ITERATIONS = 6


class Transformations(NamedTuple):
    operation: UnaryTransformation
    inverse: UnaryTransformation

    def unary(self, audio: np.ndarray, callable: UnaryTransformation) -> np.ndarray:
        return self.inverse(callable(self.operation(audio)))

    def binary(
        self,
        audio1: np.ndarray,
        audio2: np.ndarray,
        callable: BinaryTransformation,
    ) -> np.ndarray:
        return self.inverse(callable(self.operation(audio1), self.operation(audio2)))

    def multiply(
        self,
        audio: np.ndarray,
        scalar: float,
        callable: UnaryTransformation,
    ) -> np.ndarray:
        return self.inverse(callable(self.operation(audio) * scalar))


@dataclass(frozen=True)
class LinearExponentialMorpher:
    gamma: float

    p: float = field(init=False)
    a: float = field(init=False)
    transformations: Transformations = field(init=False)

    def __post_init__(self):
        if not isinstance(self.gamma, float):
            raise TypeError(f"The gamma parameter must be a float, got {type(self.gamma)}")

        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError(f"The gamma parameter must be in the range [0, 1], got {self.gamma}")

        if self.gamma == 0.0:
            p = 0.0
            interpolation = identity
            derivative = zero
            inverse = identity

        elif self.gamma == 1.0:
            p = float("inf")
            interpolation = expm1
            derivative = exp
            inverse = log1p

        else:
            p = self.gamma / (1.0 - self.gamma)
            a = p + 2.0

            def interpolation(x: np.ndarray) -> np.ndarray:
                return np.exp(x) * gammaincc(a, x) - 1.0

            def derivative(x: np.ndarray) -> np.ndarray:
                return np.exp(x) * gammaincc(a, x) - (x ** (a - 1)) / gamma(a)

            def inverse(x: np.ndarray) -> np.ndarray:
                x = np.asarray(x, dtype=float)
                z = np.log1p(x)

                for _ in range(ITERATIONS):
                    fx = interpolation(z) - x
                    fpx = derivative(z)
                    z -= fx / fpx

                return z

        object.__setattr__(self, "p", p)
        object.__setattr__(self, "a", p + 2.0 if np.isfinite(p) else float("inf"))
        object.__setattr__(self, "transformations", Transformations(interpolation, inverse))
