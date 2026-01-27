from __future__ import annotations

from functools import reduce
from typing import NamedTuple, Union, overload

import numpy as np

from sampletones.types.array import ArrayOrNumeric, BinaryTransformation, MultaryTransformation, UnaryTransformation


class Transformation(NamedTuple):
    """
    A general transformation structure that holds an operation and its inverse.

    Facilitates operations of the general form:
        `f[ op ( f^-1(x_i), i = 1 ... n) ]`

    Function `f` is called forward transformation, which sends FFT features to a transformed space,
    while `f^-1`, its inverse called backward transformation, brings the transformed features
    back to the original space.

    Operations are performed in the original space after applying the backward transformation,
    then the result is transformed back to feature space using the forward transformation.

    In particular:
    - Unary operations:
        `f[ op ( f^-1(x) ) ]`
    - Binary operations:
        `f[ op ( f^-1(x), f^-1(y) ) ]`
    - Scalar multiplication:
        `f[ f^-1( x ) ⋅ α ]`
    """

    forward: UnaryTransformation[ArrayOrNumeric]
    backward: UnaryTransformation[ArrayOrNumeric]

    def apply(
        self,
        operation: MultaryTransformation[ArrayOrNumeric],
        *arrays: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Apply a multary operation on FFT features with transformations.

        `f[ op ( f⁻¹(x₁), f⁻¹(x₂), ..., f⁻¹(xₙ) ) ]`

        Args:
            operation: Multary operation to apply.
            *arrays: Input arrays to transform.

        Returns:
            Transformed array.
        """
        return self.compose_function(operation)(*arrays)

    def reduce(
        self,
        operation: BinaryTransformation[ArrayOrNumeric],
        *arrays: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Reduce multiple FFT features using a binary operation with transformations.

            `f[ reduce( op, f⁻¹(x₁), f⁻¹(x₂), ..., f⁻¹(xₙ) ) ]`

        Applies the binary operation sequentially:

            `f[ op( ... op( op( f⁻¹(x₁), f⁻¹(x₂) ), f⁻¹(x₃) ) ..., f⁻¹(xₙ) ) ]`

        Args:
            operation: Binary operation to apply (e.g., np.add, np.multiply).
            *arrays: Input arrays/scalars to transform and reduce.

        Returns:
            Reduced and transformed array.

        Raises:
            ValueError: If fewer than one array is provided.
        """
        if len(arrays) == 0:
            raise ValueError("At least one array is required for reduce operation")

        backward = (self.backward(array) for array in arrays)
        reduced = reduce(operation, backward)
        return self.forward(reduced)

    @overload
    def compose(self, other: Transformation) -> Transformation: ...

    @overload
    def compose(self, other: MultaryTransformation[ArrayOrNumeric]) -> MultaryTransformation[ArrayOrNumeric]: ...

    def compose(
        self,
        other: Union[Transformation, MultaryTransformation[ArrayOrNumeric]],
    ) -> Union[Transformation, MultaryTransformation[ArrayOrNumeric]]:
        """
        Compose the transformation with another transformation or
        a multary function.

        Args:
            other: Other transformation/operation to compose with.

        Returns:
            Composed transformation.
        """
        if not isinstance(other, Transformation):
            return self.compose_function(other)

        return self.compose_transformation(other)

    def compose_function(
        self, operation: MultaryTransformation[ArrayOrNumeric]
    ) -> MultaryTransformation[ArrayOrNumeric]:
        """
        Compose a multary transformation with the backward operation:

            `f ∘ op ∘ f⁻¹`

        Args:
            operation: Operation to compose with.

        Returns:
            Composed multary transformation.

        Raises:
            TypeError: If operation is not callable.
        """
        if not callable(operation):
            raise TypeError("Operation must be a callable multary transformation")

        def composition(*arrays: ArrayOrNumeric) -> ArrayOrNumeric:
            backward = (self.backward(array) for array in arrays)
            return self.forward(operation(*backward))

        return composition

    def compose_transformation(self, other: Transformation) -> Transformation:
        """
        Compose two transformations. The forward transformation is:
        `g ∘ f`, while the backward transformation is:

            `f⁻¹ ∘ g⁻¹`.

        Args:
            other: Other transformation to compose with.

        Returns:
            Composed transformation.
        """

        def forward(x: ArrayOrNumeric) -> ArrayOrNumeric:
            return other.forward(self.forward(x))

        def backward(x: ArrayOrNumeric) -> ArrayOrNumeric:
            return self.backward(other.backward(x))

        return Transformation(forward, backward)

    def add(
        self,
        *arrays: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Add multiple FFT features with transformations.

            `f[ f⁻¹(x₁) + f⁻¹(x₂) + ... + f⁻¹(xₙ) ]`

        Args:
            arrays: Input arrays/scalars to transform.

        Returns:
            Transformed array.
        """

        return self.reduce(np.add, *arrays)

    def subtract(
        self,
        array1: ArrayOrNumeric,
        array2: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Subtract two FFT features with transformations.

            `f[ f⁻¹(x₁) - f⁻¹(x₂) ]`

        Args:
            array1: Minuend array/scalar to transform.
            array2: Subtrahend array/scalar to transform.

        Returns:
            Transformed array.
        """
        return self.apply(np.subtract, array1, array2)

    def multiply(
        self,
        *arrays: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Multiply multiple FFT features with transformations.

            `f[ f⁻¹(x₁) ⋅ f⁻¹(x₂) ⋅ ... ⋅ f⁻¹(xₙ) ]`

        Args:
            arrays: Input arrays/scalars to transform.

        Returns:
            Transformed array.
        """
        return self.reduce(np.multiply, *arrays)

    def divide(
        self,
        array1: ArrayOrNumeric,
        array2: ArrayOrNumeric,
    ) -> ArrayOrNumeric:
        """
        Divide two FFT features with transformations.

            `f[ f⁻¹(x₁) / f⁻¹(x₂) ]`

        Args:
            array1: Dividend array/scalar to transform.
            array2: Divisor array/scalar to transform.

        Returns:
            Transformed array.
        """
        return self.apply(np.divide, array1, array2)
