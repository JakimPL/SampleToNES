from typing import Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from sampletones.constants.general import MAX_TRANSFORMATION_GAMMA

from ..fft import calculate_fft
from .transformations import LinearExponentialMorpher, Transformations
from .typehints import BinaryTransformation, MultaryTransformation, UnaryTransformation


class FFTTransformer(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    transformations: Transformations = Field(..., description="FFT feature transformations")
    base_operation: UnaryTransformation = Field(
        default=np.abs,
        description="Base operation for FFT calculations. Default is the absolute value, change with caution",
    )

    @classmethod
    def from_gamma(cls, gamma: int) -> "FFTTransformer":
        assert 0 <= gamma <= MAX_TRANSFORMATION_GAMMA, f"Gamma must be in [0, {MAX_TRANSFORMATION_GAMMA}]"
        morpher = LinearExponentialMorpher(gamma / MAX_TRANSFORMATION_GAMMA)
        transformations = morpher.transformations
        return cls(transformations=transformations)

    def compose(self, callable: MultaryTransformation) -> MultaryTransformation:
        def composition(*args: np.ndarray) -> np.ndarray:
            return self.base_operation(callable(*args))

        return composition

    def base(self, fft: np.ndarray) -> np.ndarray:
        return self.base_operation(fft)

    def operation(self, fft: np.ndarray) -> np.ndarray:
        return self.transformations.operation(fft)

    def inverse(self, fft: np.ndarray) -> np.ndarray:
        return self.transformations.inverse(fft)

    def binary(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
        callable: BinaryTransformation,
    ) -> np.ndarray:
        binary_operation = self.compose(callable)
        return self.transformations.binary(fft1, fft2, binary_operation)

    def calculate(
        self,
        audio: np.ndarray,
        fft_size: Optional[int] = None,
    ) -> np.ndarray:
        fft = self.base_operation(calculate_fft(audio, fft_size))
        return self.transformations.inverse(fft)

    def add(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
    ) -> np.ndarray:
        return self.binary(fft1, fft2, np.add)

    def subtract(
        self,
        fft1: np.ndarray,
        fft2: np.ndarray,
    ) -> np.ndarray:
        return self.binary(fft1, fft2, np.subtract)

    def multiply(
        self,
        fft: np.ndarray,
        scalar: float,
    ) -> np.ndarray:
        return self.transformations.multiply(fft, scalar, self.base_operation)
