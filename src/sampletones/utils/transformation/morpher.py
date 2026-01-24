from dataclasses import dataclass, field
from functools import partial

from sampletones.types.array import ArrayOrScalar, UnaryTransformation

from .functions import identity, power, power_inverse
from .transformation import Transformation


@dataclass(frozen=True)
class PowerMorpher:
    """
    Provides a range of power-based transformations for FFT features,
    all of the form `x ^ a`, where `a` is derived from a gamma parameter.

    The `a` parameter is mapped from gamma in [0, 1] to [0.25, 4] such that:
        - `gamma = 0   -> a = 0.25`  (flat mapping)
        - `gamma = 0.5 -> a = 1.0`   (identity)
        - `gamma = 1   -> a = 4.0`   (sharp mapping)
    """

    gamma: float

    power: float = field(init=False)
    transformations: Transformation = field(init=False)

    def __post_init__(self) -> None:
        """
        Validate the gamma parameter and set up the transformations.

        If gamma is 0.5, the identity transformation is used.

        Raises:
            TypeError: If gamma is not a float.
            ValueError: If gamma is not in the range [0, 1].
        """
        if not isinstance(self.gamma, float):
            raise TypeError(f"The gamma parameter must be a float, got {type(self.gamma)}")

        if not 0.0 <= self.gamma <= 1.0:
            raise ValueError(f"The gamma parameter must be in the range [0, 1], got {self.gamma}")

        forward: UnaryTransformation[ArrayOrScalar]
        backward: UnaryTransformation[ArrayOrScalar]

        if self.gamma == 0.5:
            a = 1.0
            forward = identity
            backward = identity

        else:
            a = 2 ** ((self.gamma - 0.5) * 4)  # from [0, 1] to [0.25, 4]
            forward = partial(power, a=a)
            backward = partial(power_inverse, a=a)

        transformation = Transformation(forward, backward)

        object.__setattr__(self, "power", a)
        object.__setattr__(self, "transformations", transformation)
