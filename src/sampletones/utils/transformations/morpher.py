from functools import cached_property, partial

from pydantic import BaseModel, ConfigDict, Field

from sampletones.types.array import ArrayOrScalar, UnaryTransformation

from .functions import identity, power, power_inverse
from .transformation import Transformation


class PowerMorpher(BaseModel):
    """
    Provides a range of power-based transformations for FFT spectrum,
    all of the form `x ^ a`, where `a` is derived from a gamma parameter.

    The `a` parameter is mapped from gamma in [0, 1] to [0.25, 4] such that:
        - `gamma = 0.0 -> a = 0.25`  (flat mapping: makes FFT energies more comparable)
        - `gamma = 0.5 -> a = 1.0`   (identity: no transformation)
        - `gamma = 1.0 -> a = 4.0`   (sharp mapping: enhances contrast, similar to low temperature)

    Lower gamma values flatten the dynamic range, making different energy levels more uniform.
    Higher gamma values expand the dynamic range, emphasizing the most dominant frequencies.

    This class is a wrapper around `Transformation`, providing forward and backward
    transformations based on the power function. Access the transformation via the
    `.transformation` property.

    Example:
        >>> import numpy as np
        >>> morpher = PowerMorpher(gamma=0.25)
        >>> morpher.power
        0.5
        >>> result = morpher.transformation.add(3.0, 4.0)
        >>> # np.sqrt(3.0 ** 2 + 4.0 ** 2) = np.sqrt(25.0) = 5.0
        np.float64(5.0)

    Attributes:
        gamma (float): Gamma parameter in the range [0, 1] controlling the transformation
        transformation (Transformation): The forward and backward transformations.
        power (float): The power 'a' derived from the gamma parameter.
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
        The power parameter `a` derived from gamma using exponential mapping.

        The mapping is designed so that:
            - Lower gamma (< 0.5) produces a < 1.0, compressing dynamic range
            - Gamma = 0.5 produces a = 1.0, preserving values unchanged
            - Higher gamma (> 0.5) produces a > 1.0, expanding dynamic range

        Returns:
            float: The computed power `a` in the range [0.25, 4.0].
        """
        return 2 ** ((self.gamma - 0.5) * 4)

    @cached_property
    def transformation(self) -> Transformation:
        """
        Creates the power-based transformation with forward and backward functions.

        For `gamma = 0.5` (power = 1.0), returns the identity transformation.

        For all other gamma values, the transformation uses:
            - Forward: `power(x, a)` which computes `x ^ a`
            - Backward: `power_inverse(x, a)` which computes `x ^ (1 / a)`

        This allows operations to be performed in the transformed space. For example,
        with gamma=0.25 (a=0.5), adding values becomes: `√(x₁² + x₂²)`.

        Example:
            >>> import numpy as np
            >>> morpher = PowerMorpher(gamma=0.5)
            >>> morpher.transformation.add(10, 20)
            np.int64(30)
            >>> morpher = PowerMorpher(gamma=0.25)
            >>> morpher.transformation.reduce(np.add, 2.0, 3.0, 6.0)
            np.float64(7.0)

        Returns:
            Transformation: The transformation with forward=`x ^ a` and backward=`x ^ (1 / a)`.
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
