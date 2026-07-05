from __future__ import annotations

import warnings
from functools import cached_property, reduce
from types import ModuleType
from typing import (
    Dict,
    Generator,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
    overload,
)

from pydantic import ConfigDict, field_serializer, model_validator

from sampletones_core.data import DataModel
from sampletones_shared.array import xp
from sampletones_shared.exceptions import IncompleteHistogramRebinningWarning
from sampletones_shared.types.array import (
    Array,
    ArrayClasses,
    ArrayOrNumeric,
    BinaryTransformation,
    DTypeLike,
    Float,
    MultaryTransformation,
    Numeric,
    NumericClasses,
    get_array_module,
)
from sampletones_shared.types.data import SerializedData
from sampletones_shared.utils.arrays import (
    cast_to_float,
    is_increasing,
    isfinite,
)
from sampletones_shared.utils.serialization import serialize_array

from .interval import Interval


class Histogram(DataModel):
    """
    A histogram with bin edges and values.

    Represents a histogram:
        H = {(x_i)_{i=0}^n, (d_i)_{i=0}^{n-1}}

    where edges (x_i)_{i=0}^n are strictly increasing,
    and values (d_i)_{i=0}^{n-1} are arbitrary finite numeric values.

    While histograms typically represent non-negative counts or densities,
    this implementation allows any finite numeric values for mathematical generality.

    Number of edges must be exactly one more than number of values.

    Attributes:
        edges: Array of n + 1 strictly increasing bin edges.
        values: Array of n bin values.

    Examples:
        >>> import numpy as np
        >>> edges = np.array([0.0, 1.0, 4.0])  # explicit values
        >>> values = np.array([2.0, 6.0])
        >>> histogram = Histogram(edges=edges, values=values)
        >>> len(histogram)
        2
        >>> histogram.densities
        array([2., 2.])
        >>> uniform_histogram = Histogram(edges=edges, values=3.0)
        >>> uniform_histogram.values
        array([3., 9.])
        >>> uniform_histogram.densities
        array([3., 3.])
    """

    __array_priority__ = 2

    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    edges: Array
    values: Array

    @model_validator(mode="before")
    @classmethod
    def _transform_inputs(cls, data: Dict[str, Union[Array, Interval, ArrayOrNumeric]]) -> Dict[str, Array]:
        """
        Transform input data before validation.

        If edges is an Interval, converts it to an array of two edge values.

        If values is a scalar, creates a histogram with constant density
        for all bins (values will be `density ⋅ bin_width` for each bin).

        Args:
            data: Input data dictionary.

        Returns:
            Transformed data dictionary with edges and values as arrays.
        """
        data = data.copy()

        edges = data.get("edges")
        values = data.get("values")

        if edges is not None and isinstance(edges, Interval):
            edges = edges.to_array()
            data["edges"] = edges

        if values is not None and edges is not None and isinstance(values, NumericClasses):
            values = cls.density_to_values(edges, values)
            data["values"] = values

        return data

    @model_validator(mode="after")
    def _validate(self) -> Histogram:
        """
        Validate histogram structure.

        Protects edges and values from modification by setting them as read-only.

        Returns:
            The validated histogram.

        Raises:
            ValueError:
                If edges length is not values length + 1.
                If edges have fewer than 2 elements.
                If edges are not strictly increasing.
                If edges or values contain non-finite values.
                If edges are not one-dimensional.
            TypeError:
                If edges and values are not of the same type.
        """
        if len({type(self.edges), type(self.values)}) != 1:
            raise TypeError("edges and values must be of the same type")

        if self.edges.shape[-1] != self.values.shape[-1] + 1:
            raise ValueError(
                "edges should have exactly |values| + 1 elements, got "
                f"{self.edges.shape[-1]} edges and {self.values.shape[-1]} values",
            )

        if not self.edges.ndim == 1:
            raise ValueError("edges must be a one-dimensional array")

        if len(self.edges) < 2:
            raise ValueError("At least two edges are required to create a histogram")

        if not isfinite(self.edges):
            raise ValueError("edges must contain only finite values")

        if not isfinite(self.values):
            raise ValueError("values must contain only finite values")

        if not is_increasing(self.edges):
            raise ValueError("edges need to be strictly increasing")

        try:
            self.edges.setflags(write=False)
            self.values.setflags(write=False)
        except AttributeError:
            pass

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

        edges_equal: bool = self.xp.array_equal(self.edges, other.edges)
        values_equal: bool = self.xp.array_equal(self.values, other.values)
        return edges_equal and values_equal

    def __copy__(self) -> Histogram:
        """
        Create a shallow copy of the histogram.

        Returns:
            A new Histogram instance with copied edges and values.
        """
        return self.__class__(edges=self.edges, values=self.values)

    def __deepcopy__(self, memo: Optional[Dict[int, object]] = None) -> Histogram:
        """
        Create a deep copy of the histogram.

        Args:
            memo: Dictionary to track already copied objects.

        Returns:
            A new Histogram instance with deeply copied edges and values.
        """
        edges_copy = self.xp.copy(self.edges)
        values_copy = self.xp.copy(self.values)
        return self.__class__(edges=edges_copy, values=values_copy)

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

        Supports negative indices following Python conventions:
        -1 refers to the last bin, -2 to the second-to-last, etc.

        Args:
            i: Bin index (0-based, or negative for counting from end).

        Returns:
            The interval [edges[i], edges[i + 1]].

        Raises:
            IndexError: If i is out of bounds.

        Examples:
            >>> import numpy as np
            >>> histogram = Histogram(edges=np.array([0.0, 1.0, 2.0, 3.0]), values=np.array([1.0, 2.0, 3.0]))
            >>> histogram.interval(0).float()
            Interval(left=0.0, right=1.0)
            >>> histogram.interval(2).float()
            Interval(left=2.0, right=3.0)
            >>> histogram.interval(-1).float()  # last bin
            Interval(left=2.0, right=3.0)
        """
        if not -len(self) <= i < len(self):
            raise IndexError(f"Index {i} out of bounds")

        if i < 0:
            i = len(self) + i

        return Interval(self.edges[i], self.edges[i + 1])

    @classmethod
    def _from_density(
        cls,
        density: ArrayOrNumeric,
        histogram: Histogram,
    ) -> Histogram:
        """
        Create a histogram from a density operation result.

        Converts density back to values using:
            `values = density ⋅ widths`

        which preserves the relationship: `density = values / widths`.

        Args:
            density: Result of operation on densities.
            histogram: Histogram to use for edges and widths.

        Returns:
            New Histogram with transformed values.
        """
        values: Array = density * histogram.widths
        return cls(edges=histogram.edges.copy(), values=values)

    @classmethod
    def _validate_histogram_edges(cls, *histograms: Histogram, equal_edges: bool = True) -> None:
        """
        Validate that all histograms have the same edges.
        Used for operations requiring aligned histograms,
        like `apply` or `reduce`.

        Args:
            *histograms: Histograms to validate.
            equal_edges: If True, checks that all histograms have identical edges.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges, when `equal_edges` is True.
            TypeError: If histograms are of different array types.
        """
        if len(histograms) == 0:
            raise ValueError("At least one histogram is required")

        types = {type(histogram.edges) for histogram in histograms}
        if len(types) != 1:
            raise TypeError(f"All histograms must be of the same array type, got {', '.join(str(t) for t in types)}")

        module = cls.get_module(histograms[0])
        edges = histograms[0].edges
        if equal_edges and not all(module.array_equal(histogram.edges, edges) for histogram in histograms):
            raise ValueError("All histograms must have the same edges")

    def _validate_array_lengths(self, *arrays: Array) -> None:
        """
        Validate that all arrays have the same length as this histogram's values.

        Args:
            *arrays: Arrays to validate.

        Raises:
            ValueError: If any array length doesn't match values length.
        """
        length = len(self.values)
        for array in arrays:
            if len(array) != length:
                raise ValueError(f"Array length {len(array)} must match values length {length}")

    @classmethod
    def _validate_negative_power(
        cls,
        base: Union[Numeric, Array, Histogram],
        exponent: Union[Numeric, Array, Histogram],
    ) -> None:
        """
        Validate that no zero densities are raised to negative powers.

        Args:
            base: Base to validate against. Can be scalar, array, or histogram.
            exponent: Exponent to validate against. Can be scalar, array, or histogram.

        Raises:
            ZeroDivisionError: If any zero density is raised to a negative power.
            TypeError: If base or exponent are of unsupported types.
        """
        if not isinstance(base, (*NumericClasses, *ArrayClasses, cls)):
            raise TypeError(f"Unsupported base type: {type(base)}, expected Numeric, Array, or Histogram")

        if not isinstance(exponent, (*NumericClasses, *ArrayClasses, cls)):
            raise TypeError(f"Unsupported exponent type: {type(exponent)}, expected Numeric, Array, or Histogram")

        module = cls.get_module(base)
        if cls.get_module(exponent) != module:
            raise TypeError("Base and exponent must be of the same array type")

        if isinstance(base, NumericClasses) and isinstance(exponent, NumericClasses):
            if base == 0 and exponent < 0:
                raise ZeroDivisionError("Zero cannot be raised to a negative power")

        if isinstance(base, cls):
            base = base.densities

        if isinstance(exponent, cls):
            exponent = exponent.densities
        elif isinstance(exponent, NumericClasses):
            exponent = module.full_like(base, exponent)

        if isinstance(base, NumericClasses):
            base = module.full_like(exponent, base)

        assert isinstance(base, ArrayClasses), "base must be an Array"
        assert isinstance(exponent, ArrayClasses), "exponent must be an Array"
        invalid_mask = (base == 0) & (exponent < 0)
        if module.any(invalid_mask):
            raise ZeroDivisionError("Zero densities cannot be raised to negative powers")

    def apply_with(
        self,
        function: MultaryTransformation[ArrayOrNumeric],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Apply a function to this histogram's densities along with other histograms.

        Convenience method that calls Histogram.apply with self as the first argument.

        Args:
            function: Function to apply to densities.
            *histograms: Additional histograms to use as arguments.

        Returns:
            New Histogram with transformed values.

        Raises:
            ValueError: If histograms have different edges.
            TypeError: If histograms are of different array types.
        """
        return self.__class__.apply(function, self, *histograms)

    @classmethod
    def apply(
        cls,
        function: MultaryTransformation[ArrayOrNumeric],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Apply a function to histogram densities.

        Operations are performed on densities (`values / widths`), then converted
        back to values (`density ⋅ widths`). This ensures operations are independent
        of bin widths.

        Args:
            function: Function to apply to densities.
            *histograms: Histograms to use as arguments.

        Returns:
            New Histogram with transformed values.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges.
            TypeError: If histograms are of different array types.
        """
        cls._validate_histogram_edges(*histograms)
        densities = (histogram.densities for histogram in histograms)
        new_density = function(*densities)
        return cls._from_density(new_density, histograms[0])

    def reduce_with(
        self,
        function: BinaryTransformation[ArrayOrNumeric],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Reduce this histogram with others using a binary operation on densities.

        Convenience method that calls Histogram.reduce with self as the first argument.

        Args:
            function: Binary operation to reduce histograms (e.g., np.add, np.multiply).
            *histograms: Additional histograms to reduce with.

        Returns:
            Reduced histogram.

        Raises:
            ValueError: If histograms have different edges.
            TypeError: If histograms are of different array types.
        """
        return self.__class__.reduce(function, self, *histograms)

    @classmethod
    def reduce(
        cls,
        function: BinaryTransformation[ArrayOrNumeric],
        *histograms: Histogram,
    ) -> Histogram:
        """
        Reduce multiple histograms into one using the specified operation.

        Operations are performed on densities (`values / widths`), then converted
        back to values (`density ⋅ widths`).

        Args:
            function: Binary operation to reduce histograms (e.g., np.add, np.multiply).
            *histograms: Histograms to reduce.

        Returns:
            Reduced histogram.

        Raises:
            ValueError: If no histograms are provided.
            ValueError: If histograms have different edges.
            TypeError: If histograms are of different array types.
        """
        cls._validate_histogram_edges(*histograms)

        if len(histograms) == 1:
            return histograms[0]

        densities: Generator[ArrayOrNumeric] = (histogram.densities for histogram in histograms)
        new_density = reduce(function, densities)
        return cls._from_density(new_density, histograms[0])

    @classmethod
    def refine(cls, *histograms: Histogram) -> Tuple[Histogram, ...]:
        """
        Rebin multiple histograms to the union of all their edge points.

        Creates a unified edge set containing all unique edges from all histograms
        (sorted in ascending order), then rebins each histogram to this common binning.
        This enables arithmetic operations between histograms of different edges.

        Args:
            *histograms: Histograms to refine.

        Returns:
            Tuple of histograms rebinned to the unified edge set.

        Raises:
            ValueError: If no histograms are provided.
            TypeError: If histograms are of different array types.
        """
        cls._validate_histogram_edges(*histograms, equal_edges=False)
        module = cls.get_module(histograms[0])
        all_edges: Array = module.concatenate([histogram.edges for histogram in histograms])
        merged_edges: Array = cast_to_float(module.unique(all_edges))
        return tuple(histogram.rebin(merged_edges) for histogram in histograms)

    @classmethod
    def density_to_values(
        cls,
        edges: Union[Array, Histogram],
        density: Numeric,
    ) -> Array:
        """
        Convert density array to values array using histogram edges.

        Args:
            edges: Histogram or array of bin edges.
            density: Density value to convert.

        Returns:
            Array of histogram values corresponding to the density.
        """
        num_bins: int
        module: ModuleType
        if isinstance(edges, cls):
            edges = edges.edges

        elif not isinstance(edges, ArrayClasses):
            raise TypeError(f"edges must be an Array or Histogram, got {type(edges)}")

        num_bins = len(edges) - 1
        module = cls.get_module(edges)
        edges = module.diff(edges)
        values: Array = module.full(num_bins, density * edges)
        return values

    @classmethod
    def from_constant(
        cls,
        density: Numeric,
        edges: Array,
    ) -> Histogram:
        """
        Create a histogram with constant densities.

        Args:
            density: Constant density for all bins.
            edges: Array of bin edges.

        Returns:
            Histogram with constant densities.
        """
        values: Array = cls.density_to_values(edges, density)
        return cls(edges=edges, values=values)

    def astype(self, dtype: DTypeLike) -> Histogram:
        """
        Cast edges and values to a specified data type.

        Args:
            dtype: Target data type (e.g., np.float32, np.float64).

        Returns:
            New histogram with edges and values cast to the specified type.
        """
        return self.__class__(edges=self.edges.astype(dtype), values=self.values.astype(dtype))

    def rebin(
        self,
        target_bins: Union[Array, Interval, Histogram],
    ) -> Histogram:
        """
        Rebin the histogram to new bins.

        Creates a new histogram by interpolating values to match target bin edges.
        Uses linear interpolation of the cumulative distribution function (CDF),
        then takes differences to obtain new bin values.

        Args:
            target_bins: New bin specification. Can be a single Interval,
                array of edges, or another Histogram to match its bins.

        Returns:
            New histogram with rebinned values.

        Raises:
            TypeError: If target_bins is not Interval, Array, or Histogram.
            ValueError: If target edges are not strictly increasing.

        Warnings:
            RuntimeWarning: If target range doesn't contain histogram range.
        """
        edges: Array
        if isinstance(target_bins, Interval):
            edges = self.xp.array([target_bins.left, target_bins.right])

        elif isinstance(target_bins, Histogram):
            histogram: Histogram = target_bins
            edges = histogram.edges.copy()

        elif isinstance(target_bins, ArrayClasses):
            if not is_increasing(target_bins):
                raise ValueError("array of edges need to be strictly increasing")

            edges = target_bins.copy()

        else:
            raise TypeError(f"Unsupported target_bins, expected Interval, Array, or Histogram, got {type(target_bins)}")

        self.validate_overlap(edges)
        return self._rebin(edges)

    def validate_overlap(self, edges: Array) -> None:
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
                IncompleteHistogramRebinningWarning,
            )

    def _rebin(self, target_bins: Array) -> Histogram:
        """
        Internal rebinning using cumulative sum interpolation.

        Always casts integers to at least float32. Ensures that created histogram's
        edges and values are of compatible dtypes.

        Args:
            target_bins: Array of target bin edges.

        Returns:
            Rebinned histogram.

        Raises:
            TypeError: If target_bins is not an Array.
            ValueError: If target_bins are not strictly increasing.
        """
        if not isinstance(target_bins, ArrayClasses):
            raise TypeError(f"target_bins must be an Array, got {type(target_bins)}")

        if not is_increasing(target_bins):
            raise ValueError("array of edges need to be strictly increasing")

        target_bins = cast_to_float(target_bins)
        assert isinstance(target_bins, ArrayClasses), "target_bins expected to be Array after cast_to_float"

        zero = self.xp.array([0.0], dtype=self.xp.float32)
        dtype = self.xp.promote_types(self.xp.float32, self.values.dtype)
        dtype = self.xp.promote_types(dtype, target_bins.dtype)
        cumsum: Array = self.xp.concatenate([zero, self.xp.cumsum(self.values, dtype=dtype)], dtype=dtype)
        interpolation: Array = self.xp.interp(
            target_bins,
            self.edges,
            cumsum,
            left=cumsum[0],
            right=cumsum[-1],
        )
        edges: Array = target_bins.astype(dtype)
        values: Array = self.xp.diff(interpolation).astype(dtype)
        return self.__class__(edges=edges, values=values)

    @cached_property
    def range(self) -> Interval:
        """
        The total range covered by the histogram.

        Returns:
            Interval from first to last edge.
        """
        return Interval(self.edges[0], self.edges[-1])

    @cached_property
    def widths(self) -> Array:
        """
        Width of each bin.

        Returns:
            Array of bin widths (differences between consecutive edges).
        """
        return self.xp.diff(self.edges)

    def width(self, i: int) -> Float:
        """
        Width of the i-th bin.

        Args:
            i: Bin index.

        Returns:
            The width of bin i.
        """
        width: Float = self.widths[i]
        return width

    def density(self, i: int) -> Float:
        """
        Density of the i-th bin (value per unit length).

        Args:
            i: Bin index.

        Returns:
            values[i] / interval_length.
        """
        interval = self.interval(i)
        density: Float = self.values[i] / interval.length
        return density

    @cached_property
    def densities(self) -> Array:
        """
        Densities for all bins.

        Returns:
            Array of densities (values / widths) for each bin.
        """
        densities: List[Float] = [self.density(i) for i in range(len(self))]
        return self.xp.array(densities, dtype=self.values.dtype)

    @cached_property
    def total(self) -> Float:
        """
        Total sum of histogram values.

        Preserves the dtype of values.

        Returns:
            Sum of all values in the histogram.
        """
        return self.xp.sum(self.values, dtype=self.values.dtype)

    def iterate(self) -> Iterator[Tuple[Interval, Float]]:
        """
        Iterate over (interval, value) pairs.

        Yields:
            Tuples of (Interval, value) for each bin.
        """
        for i in range(len(self)):
            yield self.interval(i), self.values[i]

    @cached_property
    def xp(self) -> ModuleType:
        """
        Get the array module (NumPy or CuPy) based on the edges array type.

        Returns:
            The array module corresponding to the edges array type.
        """
        return self.__class__.get_module(self.edges)

    @classmethod
    def get_module(cls, obj: Union[Numeric, Array, Histogram]) -> ModuleType:
        """
        Get the array module (NumPy or CuPy) based on the object type.

        Args:
            obj: Histogram, Array, or Numeric to determine the module for.

        Returns:
            The array module corresponding to the object type.

        Raises:
            TypeError: If obj is not Histogram, Array, or Numeric.
        """
        if isinstance(obj, cls):
            return obj.xp

        return get_array_module(obj)

    def to_cupy(self) -> Histogram:
        """
        Convert histogram to CuPy arrays.

        Returns:
            New Histogram with edges and values as CuPy arrays.
        """
        edges = xp.asarray(self.edges)
        values = xp.asarray(self.values)
        return self.__class__(edges=edges, values=values)

    @overload
    def __add__(self, other: Histogram) -> Histogram: ...

    @overload
    def __add__(self, other: Numeric) -> Histogram: ...

    @overload
    def __add__(self, other: Array) -> Histogram: ...

    def __add__(self, other: Union[Numeric, Array, Histogram]) -> Histogram:
        """
        Add another histogram, array, or scalar to this histogram.

        For Histogram: Merges edges from both histograms, rebins to the union,
        then adds values pointwise. This is equivalent to adding densities and
        converting back to values, since after rebinning both histograms share
        the same bin widths.

        For Array: Adds array directly to values (array length must match values length).

        For scalar: Adds constant to densities, then converts back to values.

        Args:
            other: Histogram, array, or scalar to add.

        Returns:
            New histogram with the sum.

        Raises:
            ValueError: If array length doesn't match values length.
            TypeError: If other is not Histogram, Array, or Numeric.
        """
        if isinstance(other, NumericClasses):
            return self.apply_with(lambda d: d + other)

        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = Histogram.refine(self, other)
            return self.__class__(
                edges=rebinned_self.edges,
                values=rebinned_self.values + rebinned_other.values,
            )

        if isinstance(other, ArrayClasses):
            self._validate_array_lengths(other)
            return self.__class__(edges=self.edges.copy(), values=self.values + other)

        raise TypeError(f"Unsupported type for addition: {type(other)}, expected Histogram, Array, or Numeric")

    @overload
    def __radd__(self, other: Numeric) -> Histogram: ...

    @overload
    def __radd__(self, other: Array) -> Histogram: ...

    def __radd__(self, other: Union[Numeric, Array]) -> Histogram:
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
    def __mul__(self, other: Numeric) -> Histogram: ...

    @overload
    def __mul__(self, other: Array) -> Histogram: ...

    def __mul__(self, other: Union[Numeric, Array, Histogram]) -> Histogram:
        """
        Multiply this histogram by another histogram, array, or scalar.

        For Histogram: Merges edges from both histograms, rebins to the union,
        then multiplies densities pointwise and converts back to values.

        For Array: Multiplies array directly with values (array length must match values length).

        For scalar: Multiplies values directly by constant (equivalent to multiplying densities).

        Args:
            other: Histogram, array, or scalar to multiply.

        Returns:
            New histogram with the product.

        Raises:
            ValueError: If array length doesn't match values length.
            TypeError: If other is not Histogram, Array, or Numeric.
        """
        if isinstance(other, NumericClasses):
            return self.__class__(edges=self.edges.copy(), values=self.values * other)

        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = self.__class__.refine(self, other)
            return rebinned_self.reduce_with(rebinned_self.xp.multiply, rebinned_other)

        if isinstance(other, ArrayClasses):
            self._validate_array_lengths(other)
            other_histogram = self.__class__(edges=self.edges.copy(), values=other)
            return self.reduce_with(self.xp.multiply, other_histogram)

        raise TypeError(f"Unsupported type for multiplication: {type(other)}, expected Histogram, Array, or Numeric")

    @overload
    def __rmul__(self, other: Numeric) -> Histogram: ...

    @overload
    def __rmul__(self, other: Array) -> Histogram: ...

    def __rmul__(self, other: Union[Numeric, Array]) -> Histogram:
        """
        Right multiplication: support `array ⋅ histogram` and `scalar ⋅ histogram`.

        Args:
            other: Array or scalar to multiply.

        Returns:
            New histogram with the product.
        """
        return self.__mul__(other)

    @overload
    def __pow__(self, other: Histogram) -> Histogram: ...

    @overload
    def __pow__(self, other: Numeric) -> Histogram: ...

    @overload
    def __pow__(self, other: Array) -> Histogram: ...

    def __pow__(self, other: Union[Numeric, Array, Histogram]) -> Histogram:
        """
        Raise histogram to a power (applies exponent to densities).

        For Histogram: Merges edges from both histograms, rebins to the union,
        then raises densities pointwise and converts back to values.

        For Array: Raises densities to array exponents (array length must match values length).

        For scalar: Raises densities to scalar exponent.

        Args:
            other: Histogram, array, or scalar exponent.

        Returns:
            New histogram with densities raised to the given power.

        Raises:
            ZeroDivisionError: If raising to a negative power with zero densities.
            ValueError: If array length doesn't match values length.
            TypeError: If other is not Histogram, Array, or Numeric.
        """
        if isinstance(other, NumericClasses):
            self._validate_negative_power(self, other)
            return self.apply_with(lambda d: d**other)

        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = self.__class__.refine(self, other)
            rebinned_self._validate_negative_power(rebinned_self, rebinned_other)
            return rebinned_self.reduce_with(rebinned_self.xp.power, rebinned_other)

        if isinstance(other, ArrayClasses):
            self._validate_array_lengths(other)
            self._validate_negative_power(self, other)
            other_histogram = self.__class__(edges=self.edges.copy(), values=other)
            return self.reduce_with(self.xp.power, other_histogram)

        raise TypeError(f"Unsupported type for power: {type(other)}, expected Histogram, Array, or Numeric")

    @overload
    def __rpow__(self, other: Numeric) -> Histogram: ...

    @overload
    def __rpow__(self, other: Array) -> Histogram: ...

    def __rpow__(self, other: Union[Numeric, Array]) -> Histogram:
        """
        Right power: support `array ** histogram` and `scalar ** histogram`.

        Args:
            other: Array or scalar base to raise to histogram's densities.

        Returns:
            New histogram with other raised to histogram's densities.

        Raises:
            ValueError: If array length doesn't match values length.
            TypeError: If other is not Array or Numeric.
        """
        if isinstance(other, NumericClasses):
            self._validate_negative_power(self, other)
            return self.apply_with(lambda d: other**d)

        if isinstance(other, ArrayClasses):
            self._validate_negative_power(self, other)
            self._validate_array_lengths(other)
            other_histogram = self.__class__(edges=self.edges.copy(), values=other)
            return other_histogram.reduce_with(self.xp.power, self)

        raise TypeError(f"Unsupported type for power: {type(other)}, expected Array or Numeric")

    @overload
    def __sub__(self, other: Histogram) -> Histogram: ...

    @overload
    def __sub__(self, other: Numeric) -> Histogram: ...
    @overload
    def __sub__(self, other: Array) -> Histogram: ...

    def __sub__(self, other: Union[Numeric, Array, Histogram]) -> Histogram:
        """
        Subtract another histogram, array, or scalar from this histogram.

        Implemented as `self + (-1) ⋅ other`.

        Args:
            other: Histogram, array, or scalar to subtract.

        Returns:
            New histogram with the difference.

        Raises:
            ValueError: If array length doesn't match values length.
        """
        return self.__add__(-other)

    def __neg__(self) -> Histogram:
        """
        Multiply histogram by -1.

        Returns:
            New histogram with multiplied values.
        """
        return self.__mul__(-1)

    @overload
    def __rsub__(self, other: Numeric) -> Histogram: ...

    @overload
    def __rsub__(self, other: Array) -> Histogram: ...

    def __rsub__(self, other: Union[Numeric, Array]) -> Histogram:
        """
        Right subtraction: support `array - histogram` and `scalar - histogram`.

        Implemented as `other + (-1) ⋅ self`.

        Args:
            other: Array or scalar to subtract from.

        Returns:
            New histogram with the difference.
        """
        return (-self).__add__(other)

    @overload
    def __truediv__(self, other: Histogram) -> Histogram: ...

    @overload
    def __truediv__(self, other: Numeric) -> Histogram: ...

    @overload
    def __truediv__(self, other: Array) -> Histogram: ...

    def __truediv__(self, other: Union[Numeric, Array, Histogram]) -> Histogram:
        """
        Divide this histogram by another histogram, array, or scalar.

        For Histogram: Implemented as `self ⋅ other⁻¹`.
        For Array/scalar: Divides values directly.

        Args:
            other: Histogram, array, or scalar to divide by.

        Returns:
            New histogram with the quotient.

        Raises:
            ValueError: If array length doesn't match values length.
            TypeError: If other is not Histogram, Array, or Numeric.
            ZeroDivisionError: If dividing by zero.
        """
        if isinstance(other, NumericClasses):
            if other == 0.0:
                raise ZeroDivisionError("Division by zero scalar is not allowed")

            return self.__class__(edges=self.edges.copy(), values=self.values / other)

        if isinstance(other, Histogram):
            rebinned_self, rebinned_other = self.__class__.refine(self, other)
            return rebinned_self.__mul__(rebinned_other**-1)

        if isinstance(other, ArrayClasses):
            self._validate_array_lengths(other)
            if self.xp.any(other == 0.0):
                raise ZeroDivisionError("Division by zero in array is not allowed")
            return self.__class__(edges=self.edges.copy(), values=self.values / other)

        raise TypeError(f"Unsupported type for division: {type(other)}, expected Histogram, Array, or Numeric")

    @overload
    def __rtruediv__(self, other: Numeric) -> Histogram: ...

    @overload
    def __rtruediv__(self, other: Array) -> Histogram: ...

    def __rtruediv__(self, other: Union[Numeric, Array]) -> Histogram:
        """
        Right division: support `array / histogram` and `scalar / histogram`.

        Implemented as `self⁻¹ ⋅ other`.

        Args:
            other: Array or scalar to divide.

        Returns:
            New histogram with the quotient.
        """
        return (self**-1).__mul__(other)

    @field_serializer("edges", "values")
    def _serialize_array(self, array: Array) -> SerializedData:
        return serialize_array(array)
