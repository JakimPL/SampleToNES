from typing import Callable, NamedTuple, Optional, Tuple

import numpy as np

UnaryTransformation = Callable[[np.ndarray], np.ndarray]
BinaryTransformation = Callable[[np.ndarray, np.ndarray], np.ndarray]


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


IDENTITY_TRANSFORMATION = Transformations(lambda x: x, lambda x: x)
EXPONENTIAL_TRANSFORMATION = Transformations(np.expm1, np.log1p)
DEFAULT_TRANSFORMATION = IDENTITY_TRANSFORMATION
