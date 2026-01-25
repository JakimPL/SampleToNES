from __future__ import annotations

from functools import reduce
from typing import NamedTuple, Union, overload

import numpy as np

from sampletones.types.array import ArrayOrScalar, BinaryTransformation, MultaryTransformation, UnaryTransformation


class Transformation(NamedTuple):
    """
    A general transformation structure that holds an operation and its inverse.

    Facilitates operations of the general form:
        `f^-1[ op ( f(x_i), i = 1 ... n) ]`

    Function `f` is called forward transformation, which sends FFT features to a transformed space,
    while `f^-1`, its inverse called backward transformation, brings the transformed features
    back to the original space.

    In particular:
    - Unary operations:
        `f^-1[ op ( f(x) ) ]`
    - Binary operations:
        `f^-1[ op ( f(x), f(y) ) ]`
    - Scalar multiplication:
        `f^-1[ f( x ) ⋅ α ]`
    """

    forward: UnaryTransformation[ArrayOrScalar]
    backward: UnaryTransformation[ArrayOrScalar]

    def apply(
        self,
        operation: MultaryTransformation[ArrayOrScalar],
        *arrays: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Apply a multary operation on FFT features with transformations.

        `f[ op ( f^-1(x_1), f^-1(x_2), ..., f^-1(x_n) ) ]`

        Args:
            operation: Multary operation to apply.
            *arrays: Input arrays to transform.

        Returns:
            Transformed array.
        """
        return self.compose_function(operation)(*arrays)

    def reduce(
        self,
        operation: BinaryTransformation[ArrayOrScalar],
        *arrays: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Reduce multiple FFT features using a binary operation with transformations.

        `f[ reduce( op, f^-1(x_1), f^-1(x_2), ..., f^-1(x_n) ) ]`

        Applies the binary operation sequentially:
        `f[ op( ... op( op( f^-1(x_1), f^-1(x_2) ), f^-1(x_3) ) ..., f^-1(x_n) ) ]`

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
    def compose(self, other: MultaryTransformation[ArrayOrScalar]) -> MultaryTransformation[ArrayOrScalar]: ...

    def compose(
        self,
        other: Union[Transformation, MultaryTransformation[ArrayOrScalar]],
    ) -> Union[Transformation, MultaryTransformation[ArrayOrScalar]]:
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

    def compose_function(self, operation: MultaryTransformation[ArrayOrScalar]) -> MultaryTransformation[ArrayOrScalar]:
        """
        Compose a multary transformation with the backward operation.

        `f ∘ op ∘ f^-1`

        Args:
            operation: Operation to compose with.

        Returns:
            Composed multary transformation.
        """
        if not callable(operation):
            raise TypeError("Operation must be a callable multary transformation")

        def composition(*arrays: ArrayOrScalar) -> ArrayOrScalar:
            backward = (self.backward(array) for array in arrays)
            return self.forward(operation(*backward))

        return composition

    def compose_transformation(self, other: Transformation) -> Transformation:
        """
        Compose two transformations. The forward transformation is:
        `g ∘ f`, while the backward transformation is:
        `f^-1 ∘ g^-1`.

        Args:
            other: Other transformation to compose with.

        Returns:
            Composed transformation.
        """
        if not isinstance(other, Transformation):
            raise TypeError("Other must be a Transformation instance")

        def forward(x: ArrayOrScalar) -> ArrayOrScalar:
            return other.forward(self.forward(x))

        def backward(x: ArrayOrScalar) -> ArrayOrScalar:
            return self.backward(other.backward(x))

        return Transformation(forward, backward)

    def add(
        self,
        *arrays: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Add two FFT features with transformations.

        `f[ f^-1(x_1) + f^-1(x_2) + ... + f^-1(x_n) ]`

        Args:
            arrays: Input arrays/scalars to transform.

        Returns:
            Transformed array.
        """

        return self.reduce(np.add, *arrays)

    def subtract(
        self,
        array1: ArrayOrScalar,
        array2: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Subtract two FFT features with transformations.

        `f[ f^-1(x_1) - f^-1(x_2) ]`

        Args:
            array1: Minuend array/scalar to transform.
            array2: Subtrahend array/scalar to transform.

        Returns:
            Transformed array.
        """
        return self.apply(np.subtract, array1, array2)

    def multiply(
        self,
        *arrays: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Multiply two FFT features with transformations.

        `f[ f^-1(x_1) ⋅ f^-1(x_2) ⋅ ... ⋅ f^-1(x_n) ]`

        Args:
            arrays: Input arrays/scalars to transform.

        Returns:
            Transformed array.
        """
        return self.reduce(np.multiply, *arrays)

    def divide(
        self,
        array1: ArrayOrScalar,
        array2: ArrayOrScalar,
    ) -> ArrayOrScalar:
        """
        Divide two FFT features with transformations.

        `f[ f^-1(x_1) / f^-1(x_2) ]`

        Args:
            array1: Dividend array/scalar to transform.
            array2: Divisor array/scalar to transform.

        Returns:
            Transformed array.
        """
        return self.apply(np.divide, array1, array2)
