from functools import cached_property, partial

from pydantic import BaseModel, ConfigDict, Field

from sampletones_shared.types.array import ArrayOrNumeric, UnaryTransformation

from .functions import (
    identity,
    power,
    power_inverse,
    yeo_johnson,
    yeo_johnson_inverse,
    yeo_johnson_log,
    yeo_johnson_log_inverse,
)
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
        forward: UnaryTransformation[ArrayOrNumeric]
        backward: UnaryTransformation[ArrayOrNumeric]

        if self.gamma == 0.5:
            forward = identity
            backward = identity

        else:
            forward = partial(power, a=self.power)
            backward = partial(power_inverse, a=self.power)

        return Transformation(forward, backward)


class LogMorpher(BaseModel):
    """
    Provides a family of Yeo-Johnson transformations that morph continuously from
    identity (gamma = 0) to a logarithmic feature space (gamma = 1).

    The forward transformation is:

        `f_λ(x; ε) = ((x + ε)^λ - ε^λ) / λ`

    where `λ = 1 - gamma` and `ε` is the noise floor. At `gamma = 0` (λ = 1) this
    is the identity. As `gamma → 1` (λ → 0) it converges to `log(1 + x / ε)`.

    The inverse is:

        `f_λ⁻¹(y; ε) = (λy + ε^λ)^(1/λ) - ε`

    with the limit case `ε(e^y - 1)` at `gamma = 1`.

    The parameter `ε` (epsilon) is the noise floor. It defines the knee between the
    linear and logarithmic regimes: values well below `ε` are treated linearly, while
    values well above `ε` are in the log regime. It must be chosen relative to the
    meaningful signal range of the input.

    Attributes:
        gamma: Morphing parameter in [0, 1]. 0 = identity, 1 = log.
        epsilon: Noise floor. Must be positive. Caller is responsible for choosing
            a value appropriate for the expected spectrum magnitude range.
        power: Derived shape parameter λ = 1 - gamma.
        transformation: The forward and backward transformation pair.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    gamma: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Morphing parameter in [0, 1]. 0 = identity, 1 = log.",
    )
    epsilon: float = Field(
        ...,
        gt=0.0,
        description="Noise floor defining the linear-to-log transition point.",
    )

    @cached_property
    def power(self) -> float:
        """
        Shape parameter λ = 1 - gamma.

        Returns:
            float: The computed shape parameter in [0, 1].
        """
        return 1.0 - self.gamma

    @cached_property
    def transformation(self) -> Transformation:
        """
        Yeo-Johnson transformation pair for the current gamma and epsilon.

        The identity branch (gamma = 0) and log branch (gamma = 1) are handled
        explicitly rather than through the general formula, which is numerically
        unstable at the boundary values.

        Returns:
            Transformation: Forward and backward function pair.
        """
        match self.gamma:
            case 0.0:
                return Transformation(identity, identity)
            case 1.0:
                return Transformation(
                    partial(yeo_johnson_log, epsilon=self.epsilon),
                    partial(yeo_johnson_log_inverse, epsilon=self.epsilon),
                )
            case _:
                return Transformation(
                    partial(yeo_johnson, power=self.power, epsilon=self.epsilon),
                    partial(yeo_johnson_inverse, power=self.power, epsilon=self.epsilon),
                )
