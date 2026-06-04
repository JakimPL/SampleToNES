from __future__ import annotations

from typing import List, NamedTuple, Optional, Self

from sampletones_shared.types.array import (
    Array,
    ArrayClasses,
    Float,
    get_array_module,
)
from sampletones_shared.utils.arrays import is_increasing


class Interval(NamedTuple):
    """
    A closed interval [left, right] on the real line.

    An interval is valid when left < right. Invalid intervals represent
    empty sets, with zero length and no midpoint.

    Supports intersection, containment checks, and relative measure calculations.

    Attributes:
        left: The left endpoint of the interval.
        right: The right endpoint of the interval.

    Examples:
        >>> interval = Interval(3.5, 5.25)
        >>> interval.length
        1.75
        >>> interval.midpoint
        4.375
        >>> other = Interval(4.0, 6.0)
        >>> interval.intersection(other)
        Interval(left=4.0, right=5.25)
    """

    left: Float
    right: Float

    def __bool__(self) -> bool:
        """
        Check if the interval is valid.

        Returns:
            True if left < right, False otherwise.
        """
        return bool(self.left < self.right)

    @property
    def length(self) -> Float:
        """
        The length of the interval.

        Returns:
            right - left if the interval is valid, 0.0 otherwise.
        """
        if not bool(self):
            return self.zero

        return self.right - self.left

    @property
    def midpoint(self) -> Optional[Float]:
        """
        The midpoint of the interval.

        If the interval is invalid, the midpoint is undefined,
        so `None` is returned.

        Returns:
            (left + right) / 2 if the interval is valid, None otherwise.
        """
        if not bool(self):
            return None

        return 0.5 * (self.left + self.right)

    @property
    def zero(self) -> Float:
        """
        Zero of the interval content type.

        Amalgamates the type of left and right to produce zero.

        Returns:
            Zero value of the interval's endpoint type.
        """
        return type(self.left)(0) + type(self.right)(0)

    def intersection(self, other: Self) -> Self:
        """
        The intersection of this interval with another.

        Computes [max(a, c), min(b, d)] for intervals [a, b] and [c, d].
        Returns an empty interval if they don't overlap.

        Args:
            other: The interval to intersect with.

        Returns:
            The intersection interval.

        Raises:
            TypeError: If other is not an Interval.

        Examples:
            >>> Interval(1.0, 5.0).intersection(Interval(3.0, 7.0))
            Interval(left=3.0, right=5.0)
            >>> Interval(1.0, 3.0).intersection(Interval(5.0, 7.0))  # empty interval
            Interval(left=5.0, right=3.0)
        """
        if not isinstance(other, Interval):
            raise TypeError(f"Expected Interval, got {type(other)}")

        left = max(self.left, other.left)
        right = min(self.right, other.right)
        return self.__class__(left, right)

    def contains(self, other: Self) -> bool:
        """
        Check if this interval contains another interval.

        Invalid intervals (empty sets) are contained in every interval.
        Valid intervals cannot be contained in invalid intervals.

        Args:
            other: The interval to check.

        Returns:
            True if other is contained within this interval, False otherwise.

        Examples:
            >>> Interval(1.0, 10.0).contains(Interval(3.0, 7.0))
            True
            >>> Interval(1.0, 5.0).contains(Interval(3.0, 7.0))
            False
            >>> Interval(1.0, 10.0).contains(Interval(5.0, 3.0))  # invalid interval
            True
            >>> Interval(5.0, 3.0).contains(Interval(1.0, 10.0))  # invalid contains valid
            False
        """
        if not bool(other):
            return True

        if not bool(self):
            return False

        return bool(self.left <= other.left and self.right >= other.right)

    def relative_measure(self, other: Self) -> Float:
        """
        The fraction of this interval covered by another interval.

        Computes:
            `μ(other) = λ(self ∩ other) / λ(self)`

        where `λ` is the standard length of a subset of the real line.

        Args:
            other: The interval to compute relative measure with.

        Returns:
            Fraction of this interval covered by other, in [0, 1].
            Returns 0.0 if this interval is empty.

        Raises:
            TypeError: If other is not an Interval.

        Examples:
            >>> interval = Interval(3.0, 7.0)
            >>> interval.relative_measure(Interval(4.0, 6.0))
            0.5
            >>> interval.relative_measure(Interval(6.0, 15.0))
            0.25
        """
        if not isinstance(other, Interval):
            raise TypeError(f"Expected Interval, got {type(other)}")

        if not bool(self):
            return self.zero

        return self.intersection(other).length / self.length

    def float(self) -> Interval:
        """
        Convert the interval endpoints to regular floats.

        Returns:
            A new Interval with float endpoints.

        Examples:
            >>> import numpy as np
            >>> interval = Interval(np.float32(1.5), np.float32(3.5))
            >>> interval.float()
            Interval(left=1.5, right=3.5)
        """
        return Interval(float(self.left), float(self.right))

    def to_array(self) -> Array:
        """
        Convert the interval endpoints to a 1D array.

        Returns:
            A 1D array containing [left, right].

        Examples:
            >>> import numpy as np
            >>> interval = Interval(2.0, 5.0)
            >>> interval.to_array()
            array([2., 5.])
        """
        module = get_array_module(self.left)
        return module.array([self.left, self.right])

    @staticmethod
    def unit() -> Interval:
        """
        Create a unit interval [0, 1].

        Returns:
            An Interval representing [0, 1].
        """
        return Interval(0.0, 1.0)

    @staticmethod
    def from_edges(edges: Array) -> List[Interval]:
        """
        Create a list of consecutive intervals from an array of edges.

        Given edges [x₀, x₁, ..., xₙ], this creates intervals:
        [x₀, x₁], [x₁, x₂], ..., [xₙ₋₁, xₙ]

        Args:
            edges: Strictly increasing array with at least 2 elements.

        Returns:
            List of n-1 intervals where n = len(edges)

        Raises:
            TypeError: If edges is not an Array.
            ValueError: If fewer than 2 edges are provided or edges are not strictly increasing.

        Examples:
            >>> import numpy as np
            >>> edges = np.array([0., 2., 5., 10.])
            >>> intervals = Interval.from_edges(edges)
            >>> len(intervals)
            3
            >>> intervals[0].float()
            Interval(left=0.0, right=2.0)
        """
        if not isinstance(edges, ArrayClasses):
            raise TypeError(f"edges must be an Array, got {type(edges)}")

        if len(edges) < 2:
            raise ValueError("At least two edges are required to create intervals")

        if not is_increasing(edges):
            raise ValueError("edges need to be strictly increasing")

        return [Interval(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
