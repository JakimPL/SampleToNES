from dataclasses import dataclass, field
from functools import partial
from typing import NamedTuple

import numpy as np

from ffts.transformations.functions import (
    expm1,
    general_interpolation,
    general_inverse,
    identity,
    log1p,
)
from ffts.transformations.typehints import BinaryTransformation, UnaryTransformation


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
            inverse = identity

        elif self.gamma == 1.0:
            p = float("inf")
            interpolation = expm1
            inverse = log1p

        else:
            p = self.gamma / (1.0 - self.gamma)
            a = p + 2.0

            interpolation = partial(general_interpolation, a=a)
            inverse = partial(general_inverse, a=a)

        object.__setattr__(self, "p", p)
        object.__setattr__(self, "a", p + 2.0 if np.isfinite(p) else float("inf"))
        object.__setattr__(self, "transformations", Transformations(interpolation, inverse))
