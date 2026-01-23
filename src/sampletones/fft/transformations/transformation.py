from typing import NamedTuple

import numpy as np

from .functions import identity
from .typehints import BinaryTransformation, UnaryTransformation


class Transformation(NamedTuple):
    """
    A general transformation structure that holds an operation and its inverse.

    Facilitates operations of the general form:
        `f^-1( op (f^(x_i), i = 1 ... n) )`

    Function `f` is called forward transformation, which sends FFT features to a transformed space,
    while `f^-1`, its inverse called backward transformation, brings the transformed features
    back to the original space.

    In particular:
    - Unary operations:
        `f^-1( op (f^(x)) )`
    - Binary operations:
        `f^-1( op (f^(x), f^(y)) )`
    - Scalar multiplication:
        `f^-1( f^(x) ⋅ α )`
    """

    forward: UnaryTransformation
    backward: UnaryTransformation

    def unary(
        self,
        array: np.ndarray,
        operation: UnaryTransformation,
    ) -> np.ndarray:
        """
        Apply a unary operation on an FFT feature with transformations.

        `f^-1( op (f^( x )) )`

        Args:
            array (np.ndarray): Input array to transform.
            operation (UnaryTransformation): Unary operation to apply.

        Returns:
            np.ndarray: Transformed array.
        """
        return self.backward(operation(self.forward(array)))

    def binary(
        self,
        array1: np.ndarray,
        array2: np.ndarray,
        operation: BinaryTransformation,
    ) -> np.ndarray:
        """
        Apply a binary operation on two FFT features with transformations.

        `f^-1( op (f^( x ), f^( y )) )`

        Args:
            array1 (np.ndarray): First input array to transform.
            array2 (np.ndarray): Second input array to transform.
            operation (BinaryTransformation): Binary operation to apply.

        Returns:
            np.ndarray: Transformed array.
        """
        return self.backward(operation(self.forward(array1), self.forward(array2)))

    def multiply(
        self,
        array: np.ndarray,
        scalar: float,
        operation: UnaryTransformation = identity,
    ) -> np.ndarray:
        """
        Multiply an FFT feature by a scalar with transformations.

        `f^-1( f^(x) ⋅ α )`

        Args:
            array (np.ndarray): Input array to transform.
            scalar (float): Scalar multiplier.
            operation (UnaryTransformation): Operation to apply on f^-1(x) ⋅ scalar.
                Default is identity.

        Returns:
            np.ndarray: Transformed array.
        """

        return self.backward(operation(self.forward(array) * scalar))
