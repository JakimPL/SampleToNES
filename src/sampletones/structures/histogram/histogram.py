from __future__ import annotations

import warnings
from functools import cached_property, reduce
from typing import Any, Dict, Generator, Iterator, List, Optional, Self, Tuple, Type, Union, overload

import numpy as np
from pydantic import ConfigDict, model_validator

from sampletones.data import DataModel, FlatBufferBuilderProtocol
from sampletones.data.scheme import FlatBufferReaderProtocol
from sampletones.types.array import Array, ArrayOrScalar, BinaryTransformation, Float, MultaryTransformation
from sampletones.utils import is_increasing

from .interval import Interval


class Histogram(DataModel):
    """
    A histogram with bin edges and values.

    Represents a histogram:
        H = {(x_i)_{i=0}^n, (d_i)_{i=0}^{n-1}}

    where edges (x_i)_{i=0}^n are strictly increasing,
    and values (d_i)_{i=0}^{n-1} are arbitrary numeric values.

    Number of edges must be exactly one more than number of values

    Attributes:
        edges: Array of n + 1 strictly increasing bin edges.
        values: Array of n bin values.

    Examples:
        >>> edges = np.array([0.0, 2.0, 5.0, 10.0])
        >>> values = np.array([1.0, 2.0, 1.5])
        >>> hist = Histogram(edges, values)
        >>> len(hist)
        3
        >>> hist.range.float()  # Avoid numpy float representation
        Interval(left=0.0, right=10.0)
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    edges: Array
    values: Array

    def __init__(self, edges: Array, values: Array, **data: Any) -> None:
        """
        Initialize histogram with edges and values.

        Supports positional arguments for edges and values.

        Args:
            edges: Array of n + 1 strictly increasing bin edges.
            values: Array of n bin values.
        """
        data["edges"] = edges
        data["values"] = values
        super().__init__(**data)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """
        Validate histogram structure.

        Returns:
            The validated histogram.

        Raises:
            ValueError: If edges length is not values length + 1, if fewer than 2 edges,
                or if edges are not strictly increasing.
            TypeError: If edges or values are not numpy arrays.
        """
        if not isinstance(self.edges, np.ndarray):
            raise TypeError(f"edges must be a numpy array, got {type(self.edges)}")

        if not isinstance(self.values, np.ndarray):
            raise TypeError(f"values must be a numpy array, got {type(self.values)}")

        if len(self.edges) != len(self.values) + 1:
            raise ValueError("edges should have exactly |values| + 1 elements")

        if len(self.edges) < 2:
            raise ValueError("At least two edges are required to create a histogram")

        if not is_increasing(self.edges):
            raise ValueError("edges need to be strictly increasing")

        if not self.edges.ndim == 1:
            raise ValueError("edges must be a one-dimensional array")

        return self

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another histogram.

        Args:
            other: Object to compare with.

        Returns:
            True if other is a Histogram with equal edges and values,
            False otherwise.
        """
        if not isinstance(other, Histogram):
            return False

        edges_equal = np.array_equal(self.edges, other.edges)
        values_equal = np.array_equal(self.values, other.values)
        return edges_equal and values_equal

    def __copy__(self) -> Histogram:
        """
        Create a shallow copy of the histogram.

        Returns:
            A new Histogram instance with copied edges and values.
        """
        return Histogram(edges=self.edges, values=self.values)

    def __deepcopy__(self, memo: Optional[Dict[int, object]] = None) -> Histogram:
        """
        Create a deep copy of the histogram.

        Args:
            memo: Dictionary to track already copied objects.

        Returns:
            A new Histogram instance with deeply copied edges and values.
        """
        edges_copy = np.copy(self.edges)
        values_copy = np.copy(self.values)
        return Histogram(edges=edges_copy, values=values_copy)

    def __hash__(self) -> int:
        """
        Compute hash for use in sets and dictionaries.

        Returns:
            Hash based on edges and values.
        """
        return hash((tuple(self.edges), tuple(self.values)))

    def __len__(self) -> int:
        """
        Number of bins in the histogram.

        Returns:
            The length of the values array.
        """
        return len(self.values)

    def interval(self, i: int) -> Interval:
        """
        Get the i-th bin interval.

        Args:
            i: Bin index (0-based).

        Returns:
            The interval [edges[i], edges[i + 1]].

        Raises:
            IndexError: If i is out of bounds.
        """
        if not 0 <= i < len(self):
            raise IndexError(f"Index {i} out of bounds")

        return Interval(self.edges[i], self.edges[i + 1])

    def apply_with(
        self,
        function: MultaryTransformation[ArrayOrScalar],
        *histograms: Histogram,
    ) -> Histogram:
        return Histogram.apply(function, self, *histograms)

    @staticmethod
    def _from_density(
        density: ArrayOrScalar,
        histogram: Histogram,
    ) -> Histogram:
        """
        Create a histogram from a density operation result.

        Args:
            density: Result of operation on densities.
            histogram: Histogram to use for edges and widths.

        Returns:
            New Histogram with transformed values.
        """
        values: np.ndarray = density * histogram.widths
        return Histogram(edges=histogram.edges.copy(), values=values)

    @staticmethod
    def _validate_histogram_edges(*histograms: Histogram) -> None:
        """
        Validate that all histograms have the same edges.
        Used for operations requiring aligned histograms,
        like `apply` or `reduce`.

        Args:
            *histograms: Histograms to validate.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges.
        """
        if len(histograms) == 0:
            raise ValueError("At least one histogram is required")

        edges = histograms[0].edges
        if not all(np.array_equal(histogram.edges, edges) for histogram in histograms):
            raise ValueError("All histograms must have the same edges")

    @staticmethod
    def apply(
        function: MultaryTransformation[ArrayOrScalar],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Apply a function to all histogram values. Function is applied to densities,
        and the value is recomputed to preserve total mass.

        Args:
            function: Function to apply to each value.
            *histograms: Histograms to use as arguments.

        Returns:
            New Histogram with transformed values.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges.
        """
        Histogram._validate_histogram_edges(*histograms)
        densities = (histogram.densities for histogram in histograms)
        new_density = function(*densities)
        return Histogram._from_density(new_density, histograms[0])

    @staticmethod
    def reduce(
        function: BinaryTransformation[ArrayOrScalar],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Reduce multiple histograms into one using the specified operation.

        Args:
            function: Binary operation to reduce histograms (e.g., np.add, np.multiply).
            *histograms: Histograms to reduce.

        Returns:
            Reduced histogram.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges.
        """
        Histogram._validate_histogram_edges(*histograms)

        if len(histograms) == 1:
            return histograms[0]

        densities: Generator[ArrayOrScalar] = (histogram.densities for histogram in histograms)
        new_density = reduce(function, densities)
        return Histogram._from_density(new_density, histograms[0])

    @staticmethod
    def refine(*histograms: Histogram) -> Tuple[Histogram, ...]:
        """
        Rebin multiple histograms to the union of all their edge points.

        Args:
            *histograms: Histograms to refine.

        Returns:
            Tuple of histograms rebinned to the unified edge set.

        Raises:
            ValueError: If no histograms are provided.
        """
        if len(histograms) == 0:
            raise ValueError("At least one histogram is required")

        if len(histograms) == 1:
            return (histograms[0],)

        all_edges = np.concatenate([histogram.edges for histogram in histograms])
        merged_edges = np.unique(all_edges)
        return tuple(histogram.rebin(merged_edges) for histogram in histograms)

    @staticmethod
    def from_constant(
        density: Float,
        edges: np.ndarray,
    ) -> Histogram:
        """
        Create a histogram with constant densities.

        Args:
            density: Constant density for all bins.
            edges: Array of bin edges.

        Returns:
            Histogram with constant densities.
        """
        num_bins = len(edges) - 1
        values = np.full(num_bins, density * np.diff(edges))
        return Histogram(edges=edges, values=values)

    def rebin(
        self,
        target_bins: Union[Interval, np.ndarray, Histogram],
    ) -> Histogram:
        """
        Rebin the histogram to new bins.

        Creates a new histogram by interpolating values to match
        target bin edges. Preserves total histogram mass through
        linear interpolation of cumulative sum.

        Args:
            target_bins: New bin specification. Can be a single Interval,
                array of edges, or another Histogram to match its bins.

        Returns:
            New histogram with rebinned values.

        Raises:
            TypeError: If target_bins is not Interval, np.ndarray, or Histogram.
            ValueError: If target edges are not strictly increasing.

        Warnings:
            RuntimeWarning: If target range doesn't contain histogram range.
        """
        edges: np.ndarray
        if isinstance(target_bins, Interval):
            edges = np.array([target_bins.left, target_bins.right])

        elif isinstance(target_bins, np.ndarray):
            if not is_increasing(target_bins):
                raise ValueError("array of edges need to be strictly increasing")

            edges = target_bins.copy()

        elif isinstance(target_bins, Histogram):
            histogram: Histogram = target_bins
            edges = histogram.edges.copy()

        else:
            raise TypeError(
                f"Unsupported target_bins, expected Interval, np.ndarray, or Histogram, got {type(target_bins)}"
            )

        self.validate_overlap(edges)
        return self._rebin(edges)

    def validate_overlap(self, edges: np.ndarray) -> None:
        """
        Check if target edges contain the histogram range.

        Args:
            edges: Target bin edges to validate.

        Warnings:
            RuntimeWarning: If target range doesn't fully contain histogram range.
        """
        edges_range: Interval = Interval(edges[0], edges[-1])
        if not edges_range.contains(self.range):
            warnings.warn(
                "Rebinning to intervals outside of the histogram range may lead to unexpected results",
                RuntimeWarning,
            )

    def _rebin(self, target_bins: np.ndarray) -> Histogram:
        """
        Internal rebinning using cumulative sum interpolation.

        Args:
            target_bins: Array of target bin edges.

        Returns:
            Rebinned histogram.

        Raises:
            TypeError: If target_bins is not a numpy array.
            ValueError: If target_bins are not strictly increasing.
        """
        if not isinstance(target_bins, np.ndarray):
            raise TypeError(f"target_bins must be a numpy array, got {type(target_bins)}")

        if not is_increasing(target_bins):
            raise ValueError("array of edges need to be strictly increasing")

        cumsum: np.ndarray = np.concatenate([[0], np.cumsum(self.values)])
        interpolation: np.ndarray = np.interp(
            target_bins,
            self.edges,
            cumsum,
            left=0,
            right=cumsum[-1],
        )
        values: np.ndarray = np.diff(interpolation)
        return Histogram(edges=target_bins, values=values)

    @cached_property
    def range(self) -> Interval:
        """
        The total range covered by the histogram.

        Returns:
            Interval from first to last edge.
        """
        return Interval(self.edges[0], self.edges[-1])

    @cached_property
    def widths(self) -> np.ndarray:
        """
        Width of each bin.

        Returns:
            Array of bin widths (differences between consecutive edges).
        """
        return np.diff(self.edges)

    def width(self, i: int) -> np.floating:
        """
        Width of the i-th bin.

        Args:
            i: Bin index.

        Returns:
            The width of bin i.
        """
        width: np.floating = self.widths[i]
        return width

    def density(self, i: int) -> np.floating:
        """
        Density of the i-th bin (value per unit length).

        Args:
            i: Bin index.

        Returns:
            values[i] / interval_length, or 0.0 if interval is empty.
        """
        interval = self.interval(i)
        if not interval:
            zero: np.floating = self.values.dtype.type(0.0)
            return zero

        density: np.floating = self.values[i] / interval.length
        return density

    @cached_property
    def densities(self) -> np.ndarray:
        """
        Densities for all bins.

        Returns:
            Array of densities (values / widths) for each bin.
        """
        densities: List[np.floating] = [self.density(i) for i in range(len(self))]
        return np.array(densities, dtype=self.values.dtype)

    @cached_property
    def total(self) -> np.floating:
        """
        Total sum of histogram values.

        Returns:
            Sum of all values in the histogram.
        """
        return np.sum(self.values)

    def iterate(self) -> Iterator[Tuple[Interval, np.floating]]:
        """
        Iterate over (interval, value) pairs.

        Yields:
            Tuples of (Interval, value) for each bin.
        """
        for i in range(len(self)):
            yield self.interval(i), self.values[i]

    @overload
    def __add__(self, other: Histogram) -> Histogram: ...

    @overload
    def __add__(self, other: Float) -> Histogram: ...

    @overload
    def __add__(self, other: Array) -> Histogram: ...

    def __add__(self, other: Union[Histogram, Array, Float]) -> Histogram:
        """
        Add another histogram, array, or scalar to this histogram.

        For Histogram: Merges edges from both histograms, rebins to the union,
        and adds values pointwise.

        For Array: Adds array directly to values (array length must match values length).

        For scalar: Adds constant to densities.

        Args:
            other: Histogram, array, or scalar to add.

        Returns:
            New histogram with the sum.

        Raises:
            ValueError: If array length doesn't match values length.
        """
        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = Histogram.refine(self, other)
            return Histogram(edges=rebinned_self.edges, values=rebinned_self.values + rebinned_other.values)

        if isinstance(other, np.ndarray):
            if len(other) != len(self.values):
                raise ValueError(f"Array length {len(other)} must match values length {len(self.values)}")

            return Histogram(edges=self.edges.copy(), values=self.values + other)

        return self.apply_with(lambda d: d + other)

    @overload
    def __radd__(self, other: Float) -> Histogram: ...

    @overload
    def __radd__(self, other: Array) -> Histogram: ...

    def __radd__(self, other: Union[Array, Float]) -> Histogram:
        """
        Right addition: support array + histogram and scalar + histogram.

        Args:
            other: Array or scalar to add.

        Returns:
            New histogram with the sum.
        """
        return self.__add__(other)

    @overload
    def __mul__(self, other: Histogram) -> Histogram: ...

    @overload
    def __mul__(self, other: Float) -> Histogram: ...

    @overload
    def __mul__(self, other: Array) -> Histogram: ...

    def __mul__(self, other: Union[Histogram, Array, Float]) -> Histogram:
        """
        Multiply this histogram by another histogram, array, or scalar.

        For Histogram: Merges edges from both histograms, rebins to the union,
        and multiplies densities pointwise.

        For Array: Multiplies array directly with values (array length must match values length).

        For scalar: Multiplies values directly by constant.

        Args:
            other: Histogram, array, or scalar to multiply.

        Returns:
            New histogram with the product.

        Raises:
            ValueError: If array length doesn't match values length.
        """
        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = Histogram.refine(self, other)
            return rebinned_self.apply_with(np.multiply, rebinned_other)

        if isinstance(other, np.ndarray):
            if len(other) != len(self.values):
                raise ValueError(f"Array length {len(other)} must match values length {len(self.values)}")

            other = Histogram(edges=self.edges.copy(), values=other)
            return self.apply_with(np.multiply, other)

        return Histogram(edges=self.edges.copy(), values=self.values * other)

    @overload
    def __rmul__(self, other: Float) -> Histogram: ...

    @overload
    def __rmul__(self, other: Array) -> Histogram: ...

    def __rmul__(self, other: Union[Array, Float]) -> Histogram:
        """
        Right multiplication: support array * histogram and scalar * histogram.

        Args:
            other: Array or scalar to multiply.

        Returns:
            New histogram with the product.
        """
        return self.__mul__(other)

    def __pow__(self, exponent: Float) -> Histogram:
        """
        Raise histogram to a power (applies exponent to densities).

        Args:
            exponent: Power to raise densities to.

        Returns:
            New histogram with densities raised to the given power.
        """
        return self.apply_with(lambda d: d**exponent)

    @overload
    def __sub__(self, other: Histogram) -> Histogram: ...

    @overload
    def __sub__(self, other: Float) -> Histogram: ...

    @overload
    def __sub__(self, other: Array) -> Histogram: ...

    def __sub__(self, other: Union[Histogram, Array, Float]) -> Histogram:
        """
        Subtract another histogram, array, or scalar from this histogram.

        Implemented as self + (other * -1).

        Args:
            other: Histogram, array, or scalar to subtract.

        Returns:
            New histogram with the difference.

        Raises:
            ValueError: If array length doesn't match values length.
        """
        if isinstance(other, Histogram):
            return self.__add__(other * -1)

        if isinstance(other, np.ndarray):
            return self.__add__(-other)

        return self.__add__(-other)

    @overload
    def __rsub__(self, other: Float) -> Histogram: ...

    @overload
    def __rsub__(self, other: Array) -> Histogram: ...

    def __rsub__(self, other: Union[Array, Float]) -> Histogram:
        """
        Right subtraction: support array - histogram and scalar - histogram.

        Implemented as other + (self * -1).

        Args:
            other: Array or scalar to subtract from.

        Returns:
            New histogram with the difference.
        """
        return (self * -1).__add__(other)

    @overload
    def __truediv__(self, other: Histogram) -> Histogram: ...

    @overload
    def __truediv__(self, other: Float) -> Histogram: ...

    @overload
    def __truediv__(self, other: Array) -> Histogram: ...

    def __truediv__(self, other: Union[Histogram, Array, Float]) -> Histogram:
        """
        Divide this histogram by another histogram, array, or scalar.

        For Histogram: Implemented as self * (other ** -1).
        For Array/scalar: Divides values directly.

        Args:
            other: Histogram, array, or scalar to divide by.

        Returns:
            New histogram with the quotient.

        Raises:
            ValueError: If array length doesn't match values length.
        """
        if isinstance(other, Histogram):
            return self.__mul__(other**-1)

        if isinstance(other, np.ndarray):
            if len(other) != len(self.values):
                raise ValueError(f"Array length {len(other)} must match values length {len(self.values)}")
            return Histogram(edges=self.edges.copy(), values=self.values / other)

        return Histogram(edges=self.edges.copy(), values=self.values / other)

    @overload
    def __rtruediv__(self, other: Float) -> Histogram: ...

    @overload
    def __rtruediv__(self, other: Array) -> Histogram: ...

    def __rtruediv__(self, other: Union[Array, Float]) -> Histogram:
        """
        Right division: support array / histogram and scalar / histogram.

        Implemented as (self ** -1) * other.

        Args:
            other: Array or scalar to divide.

        Returns:
            New histogram with the quotient.
        """
        return (self**-1).__mul__(other)

    @classmethod
    def buffer_builder(cls) -> FlatBufferBuilderProtocol:
        from sampletones_schemas.histogram import FBHistogram

        return FBHistogram

    @classmethod
    def buffer_reader(cls) -> Type[FlatBufferReaderProtocol]:
        from sampletones_schemas.histogram import FBHistogram

        return FBHistogram.FBHistogram
