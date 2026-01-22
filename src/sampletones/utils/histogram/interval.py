from __future__ import annotations

from typing import List, NamedTuple, Optional, Self

import numpy as np

from sampletones.types import Float

from ..common import is_increasing


class Interval(NamedTuple):
    """
    A closed interval [left, right] on the real line.

    An interval is valid when left < right.

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
            return 0.0

        return self.right - self.left

    @property
    def midpoint(self) -> Optional[Float]:
        """
        The midpoint of the interval.

        Returns:
            (left + right) / 2 if the interval is valid, None otherwise.
        """
        if not bool(self):
            return None

        return 0.5 * (self.left + self.right)

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

        Args:
            other: The interval to check.

        Returns:
            True if other is contained within this interval, False otherwise.

        Examples:
            >>> Interval(1.0, 10.0).contains(Interval(3.0, 7.0))
            True
            >>> Interval(1.0, 5.0).contains(Interval(3.0, 7.0))
            False
        """
        return bool(self.left <= other.left and self.right >= other.right)

    def relative_measure(self, other: Self) -> Float:
        """
        The fraction of this interval covered by another interval.

        Computes μ(other) = λ(self ∩ other) / λ(self) where λ is the length.
        Used in histogram rebinning to calculate bin weight contributions.

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
            return 0.0

        return self.intersection(other).length / self.length

    def float(self) -> Interval:
        """
        Convert the interval endpoints to regular floats.

        Returns:
            A new Interval with float endpoints.

        Examples:
            >>> interval = Interval(np.float32(1.5), np.float32(3.5))
            >>> interval.float()
            Interval(left=1.5, right=3.5)
        """
        return Interval(float(self.left), float(self.right))

    @classmethod
    def unit(cls) -> Self:
        """
        Create a unit interval [0, 1].

        Returns:
            An Interval representing [0, 1].
        """
        return cls(0.0, 1.0)

    @classmethod
    def from_edges(cls, edges: np.ndarray) -> List[Self]:
        """
        Create a list of consecutive intervals from an array of edges.

        Given edges [x₀, x₁, ..., xₙ], this creates intervals:
        [x₀, x₁], [x₁, x₂], ..., [xₙ₋₁, xₙ]

        Args:consecutive intervals from edge array.

        Given edges [x₀, x₁, ..., xₙ], creates intervals
        [x₀, x₁], [x₁, x₂], ..., [xₙ₋₁, xₙ].

        Args:
            edges: Strictly increasing array with at least 2 elements.

        Returns:
            List of n-1 intervals where n = len(edges)
            >>> edges = np.array([0., 2., 5., 10.])
            >>> intervals = Interval.from_edges(edges)
            >>> len(intervals)
            3
            >>> intervals[0].float()
            Interval(left=0.0, right=2.0)
        """
        if len(edges) < 2:
            raise ValueError("At least two edges are required to create intervals")

        if not is_increasing(edges):
            raise ValueError("Edges need to be strictly increasing")

        return [cls(edges[i], edges[i + 1]) for i in range(len(edges) - 1)]
