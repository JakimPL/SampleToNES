import math

from sampletones.types.array import ArrayOrNumeric, ArrayOrScalarClasses, get_array_module


def assert_array_equal(result: ArrayOrNumeric, expected: ArrayOrNumeric) -> None:
    if isinstance(result, (bool, int, float)):
        assert type(result) == type(expected)
        if isinstance(expected, float) and math.isnan(expected):
            assert math.isnan(result)
        elif isinstance(expected, float):
            assert math.isclose(result, expected, rel_tol=1e-6, abs_tol=1e-9)
        else:
            assert result == expected
    else:
        assert not isinstance(expected, (bool, int, float))
        assert isinstance(result, ArrayOrScalarClasses)
        assert isinstance(expected, ArrayOrScalarClasses)
        module = get_array_module(result)
        assert result.dtype == expected.dtype
        if module.issubdtype(result.dtype, module.floating):
            module.testing.assert_array_almost_equal(result, expected)
        else:
            module.testing.assert_array_equal(result, expected)
