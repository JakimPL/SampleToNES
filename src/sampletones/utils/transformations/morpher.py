from functools import cached_property, partial

from pydantic import BaseModel, ConfigDict, Field

from sampletones.types.array import ArrayOrScalar, UnaryTransformation

from .functions import identity, power, power_inverse
from .transformation import Transformation


class PowerMorpher(BaseModel):
    """
    Provides a range of power-based transformations for FFT features,
    all of the form `x ^ a`, where `a` is derived from a gamma parameter.

    The `a` parameter is mapped from gamma in [0, 1] to [0.25, 4] such that:
        - `gamma = 0   -> a = 0.25`  (flat mapping)
        - `gamma = 0.5 -> a = 1.0`   (identity)
        - `gamma = 1   -> a = 4.0`   (sharp mapping)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    gamma: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Gamma parameter in the range [0, 1] controlling the transformation.",
    )

    @cached_property
    def power(self) -> float:
        """
        The power 'a' derived from the gamma parameter.

        Mapped from gamma in [0, 1] to [0.25, 4].

        Returns:
            float: The computed power 'a'.
        """
        return 2 ** ((self.gamma - 0.5) * 4)

    @cached_property
    def transformation(self) -> Transformation:
        """
        Set up the transformation.

        If gamma is 0.5, the identity transformation is used.

        Returns:
            Transformation: The forward and backward transformations.
        """
        forward: UnaryTransformation[ArrayOrScalar]
        backward: UnaryTransformation[ArrayOrScalar]

        if self.gamma == 0.5:
            forward = identity
            backward = identity

        else:
            forward = partial(power, a=self.power)
            backward = partial(power_inverse, a=self.power)

        return Transformation(forward, backward)
