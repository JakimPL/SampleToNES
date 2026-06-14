from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pytest

from sampletones_shared.utils.transformations.functions import (
    exp,
    identity,
    power,
)
from sampletones_shared.utils.transformations.transformation import (
    Transformation,
)
from tests.suite.arrays import assert_array_equal
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class TestTransformationIdentity(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class ApplyTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    @dataclass(frozen=True, kw_only=True)
    class ReduceTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    identity_transformation = Transformation(forward=identity, backward=identity)

    apply_test_cases = [
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(2, 3),
            expected=np.int64(5),
            label="identity_add_int",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(2.5, 3.5),
            expected=np.float64(6.0),
            label="identity_add_float",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(2, 3),
            expected=np.int64(6),
            label="identity_multiply_int",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(2.5, 4.0),
            expected=np.float64(10.0),
            label="identity_multiply_float",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.subtract,
            inputs=(5, 3),
            expected=np.int64(2),
            label="identity_subtract_int",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.divide,
            inputs=(10.0, 2.0),
            expected=np.float64(5.0),
            label="identity_divide_float",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.int32(2), np.int32(3)),
            expected=np.int32(5),
            label="identity_add_numpy_int32",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.float64(2.5), np.float64(3.5)),
            expected=np.float64(6.0),
            label="identity_add_numpy_float64",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.array([1, 2, 3]), np.array([4, 5, 6])),
            expected=np.array([5, 7, 9]),
            label="identity_add_numpy_array",
        ),
        ApplyTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(np.array([2.0, 3.0, 4.0]), np.array([1.5, 2.5, 3.5])),
            expected=np.array([3.0, 7.5, 14.0]),
            label="identity_multiply_numpy_array",
        ),
    ]

    reduce_test_cases = [
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(1, 2, 3, 4),
            expected=np.int64(10),
            label="identity_reduce_add_four_int",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(2, 3, 4),
            expected=np.int64(24),
            label="identity_reduce_multiply_three_int",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(1.5, 2.5, 3.5),
            expected=np.float64(7.5),
            label="identity_reduce_add_three_float",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.int32(1), np.int32(2), np.int32(3)),
            expected=np.int32(6),
            label="identity_reduce_add_numpy_int32",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(np.float64(2.0), np.float64(3.0)),
            expected=np.float64(6.0),
            label="identity_reduce_multiply_numpy_float64",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.array([1, 2]), np.array([3, 4]), np.array([5, 6])),
            expected=np.array([9, 12]),
            label="identity_reduce_add_three_arrays",
        ),
        ReduceTestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(np.array([2.0, 3.0]), np.array([4.0, 5.0])),
            expected=np.array([8.0, 15.0]),
            label="identity_reduce_multiply_two_arrays",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        apply_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_apply(self, test_case: ApplyTestCase) -> None:
        result = test_case.transformation.apply(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)

    @pytest.mark.parametrize(
        "test_case",
        reduce_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_reduce(self, test_case: ReduceTestCase) -> None:
        result = test_case.transformation.reduce(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)


class TestTransformationExp(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class ApplyTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    @dataclass(frozen=True, kw_only=True)
    class ReduceTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    exp_transformation = Transformation(forward=exp, backward=np.log)

    apply_test_cases = [
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0, 3.0),
            expected=np.float64(6.0),
            label="exp_add_becomes_multiply_float",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2, 3),
            expected=np.float64(6.0),
            label="exp_add_becomes_multiply_int",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.multiply,
            inputs=(2.0, 3.0),
            expected=np.exp(np.log(2.0) * np.log(3.0)),
            label="exp_multiply_float",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.subtract,
            inputs=(6.0, 2.0),
            expected=np.float64(3.0),
            label="exp_subtract_becomes_divide_float",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.divide,
            inputs=(6.0, 2.0),
            expected=np.exp(np.log(6.0) / np.log(2.0)),
            label="exp_divide_float",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(np.float32(2.0), np.float32(3.0)),
            expected=np.float32(6.0),
            label="exp_add_numpy_float32",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(np.float64(4.0), np.float64(5.0)),
            expected=np.float64(20.0),
            label="exp_add_numpy_float64",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(np.array([2.0, 3.0, 4.0]), np.array([3.0, 4.0, 5.0])),
            expected=np.array([6.0, 12.0, 20.0]),
            label="exp_add_numpy_array",
        ),
        ApplyTestCase(
            transformation=exp_transformation,
            operation=np.multiply,
            inputs=(np.array([2.0, 3.0]), np.array([1.5, 2.5])),
            expected=np.exp(np.log(np.array([2.0, 3.0])) * np.log(np.array([1.5, 2.5]))),
            label="exp_multiply_numpy_array",
        ),
    ]

    reduce_test_cases = [
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0, 3.0, 4.0),
            expected=np.float64(24.0),
            label="exp_reduce_add_three_becomes_multiply",
        ),
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0, 3.0, 4.0, 5.0),
            expected=np.float64(120.0),
            label="exp_reduce_add_four_becomes_multiply",
        ),
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.multiply,
            inputs=(2.0, 3.0, 4.0),
            expected=np.exp(np.log(2.0) * np.log(3.0) * np.log(4.0)),
            label="exp_reduce_multiply_three",
        ),
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0,),
            expected=np.float64(2.0),
            label="exp_reduce_single_element",
        ),
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(np.float32(2.0), np.float32(3.0), np.float32(4.0)),
            expected=np.float32(24.0),
            label="exp_reduce_add_numpy_float32",
        ),
        ReduceTestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(
                np.array([2.0, 3.0]),
                np.array([4.0, 5.0]),
                np.array([6.0, 7.0]),
            ),
            expected=np.array([48.0, 105.0]),
            label="exp_reduce_add_three_arrays",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        apply_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_apply(self, test_case: ApplyTestCase) -> None:
        result = test_case.transformation.apply(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)

    @pytest.mark.parametrize(
        "test_case",
        reduce_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_reduce(self, test_case: ReduceTestCase) -> None:
        result = test_case.transformation.reduce(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)


class TestTransformationPower(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class ApplyTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    @dataclass(frozen=True, kw_only=True)
    class ReduceTestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    square_transformation = Transformation(
        forward=lambda x: power(x, 2.0),
        backward=lambda x: power(x, 0.5),
    )

    apply_test_cases = [
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(4.0, 9.0),
            expected=(np.sqrt(4.0) + np.sqrt(9.0)) ** 2,
            label="square_add_float",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(4, 9),
            expected=(np.sqrt(4) + np.sqrt(9)) ** 2,
            label="square_add_int",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.multiply,
            inputs=(4.0, 9.0),
            expected=(np.sqrt(4.0) * np.sqrt(9.0)) ** 2,
            label="square_multiply_float",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.subtract,
            inputs=(9.0, 4.0),
            expected=(np.sqrt(9.0) - np.sqrt(4.0)) ** 2,
            label="square_subtract_float",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.divide,
            inputs=(9.0, 4.0),
            expected=(np.sqrt(9.0) / np.sqrt(4.0)) ** 2,
            label="square_divide_float",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(np.float32(16.0), np.float32(25.0)),
            expected=np.float32((np.sqrt(16.0) + np.sqrt(25.0)) ** 2),
            label="square_add_numpy_float32",
        ),
        ApplyTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(np.array([4.0, 9.0, 16.0]), np.array([1.0, 4.0, 9.0])),
            expected=(np.sqrt(np.array([4.0, 9.0, 16.0])) + np.sqrt(np.array([1.0, 4.0, 9.0]))) ** 2,
            label="square_add_numpy_array",
        ),
    ]

    reduce_test_cases = [
        ReduceTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(4.0, 9.0, 16.0),
            expected=(np.sqrt(4.0) + np.sqrt(9.0) + np.sqrt(16.0)) ** 2,
            label="square_reduce_add_three_float",
        ),
        ReduceTestCase(
            transformation=square_transformation,
            operation=np.multiply,
            inputs=(4.0, 9.0),
            expected=(np.sqrt(4.0) * np.sqrt(9.0)) ** 2,
            label="square_reduce_multiply_two_float",
        ),
        ReduceTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(4,),
            expected=np.float64(4.0),
            label="square_reduce_single_element",
        ),
        ReduceTestCase(
            transformation=square_transformation,
            operation=np.add,
            inputs=(
                np.array([1.0, 4.0]),
                np.array([4.0, 9.0]),
                np.array([9.0, 16.0]),
            ),
            expected=(np.sqrt(np.array([1.0, 4.0])) + np.sqrt(np.array([4.0, 9.0])) + np.sqrt(np.array([9.0, 16.0])))
            ** 2,
            label="square_reduce_add_three_arrays",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        apply_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_apply(self, test_case: ApplyTestCase) -> None:
        result = test_case.transformation.apply(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)

    @pytest.mark.parametrize(
        "test_case",
        reduce_test_cases,
        ids=lambda tc: tc.label,
    )
    def test_reduce(self, test_case: ReduceTestCase) -> None:
        result = test_case.transformation.reduce(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)


class TestTransformationReduce(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        transformation: Transformation
        operation: Any
        inputs: Tuple[Any, ...]

    identity_transformation = Transformation(forward=identity, backward=identity)
    exp_transformation = Transformation(forward=exp, backward=np.log)

    test_cases = [
        TestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(1, 2, 3, 4),
            expected=np.int64(10),
            label="identity_reduce_add_four_int",
        ),
        TestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(2, 3, 4),
            expected=np.int64(24),
            label="identity_reduce_multiply_three_int",
        ),
        TestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(1.5, 2.5, 3.5),
            expected=np.float64(7.5),
            label="identity_reduce_add_three_float",
        ),
        TestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(5,),
            expected=5,  # identity transformation should not change type
            label="identity_reduce_single_element",
        ),
        TestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0, 3.0, 4.0),
            expected=np.float64(24.0),
            label="exp_reduce_add_three_becomes_multiply",
        ),
        TestCase(
            transformation=exp_transformation,
            operation=np.add,
            inputs=(2.0, 3.0, 4.0, 5.0),
            expected=np.float64(120.0),
            label="exp_reduce_add_four_becomes_multiply",
        ),
        TestCase(
            transformation=exp_transformation,
            operation=np.multiply,
            inputs=(2.0, 3.0, 4.0),
            expected=np.float64(np.exp(np.log(2.0) * np.log(3.0) * np.log(4.0))),
            label="exp_reduce_multiply_three",
        ),
        TestCase(
            transformation=identity_transformation,
            operation=np.add,
            inputs=(np.array([1, 2]), np.array([3, 4]), np.array([5, 6])),
            expected=np.array([9, 12]),
            label="identity_reduce_add_three_arrays",
        ),
        TestCase(
            transformation=identity_transformation,
            operation=np.multiply,
            inputs=(
                np.array([2.0, 3.0], dtype=np.float32),
                np.array([4.0, 5.0], dtype=np.float64),
            ),
            expected=np.array([8.0, 15.0]),
            label="identity_reduce_multiply_two_arrays",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_reduce(self, test_case: TestCase) -> None:
        result = test_case.transformation.reduce(test_case.operation, *test_case.inputs)
        assert_array_equal(result, test_case.expected)


class TestTransformationArithmeticMethods(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        transformation: Transformation
        method_name: str
        inputs: Tuple[Any, ...]

    identity_transformation = Transformation(forward=identity, backward=identity)
    exp_transformation = Transformation(forward=exp, backward=np.log)

    test_cases = [
        TestCase(
            transformation=identity_transformation,
            method_name="add",
            inputs=(2, 3),
            expected=np.int64(5),
            label="identity_add_two_int",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="add",
            inputs=(1, 2, 3, 4),
            expected=np.int64(10),
            label="identity_add_four_int",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="subtract",
            inputs=(5, 3),
            expected=np.int64(2),
            label="identity_subtract_int",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="multiply",
            inputs=(2, 3),
            expected=np.int64(6),
            label="identity_multiply_two_int",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="multiply",
            inputs=(2, 3, 4),
            expected=np.int64(24),
            label="identity_multiply_three_int",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="divide",
            inputs=(10.0, 2.0),
            expected=np.float64(5.0),
            label="identity_divide_float",
        ),
        TestCase(
            transformation=exp_transformation,
            method_name="add",
            inputs=(2.0, 3.0),
            expected=np.float64(6.0),
            label="exp_add_two_becomes_multiply",
        ),
        TestCase(
            transformation=exp_transformation,
            method_name="add",
            inputs=(2.0, 3.0, 4.0),
            expected=np.float64(24.0),
            label="exp_add_three_becomes_multiply",
        ),
        TestCase(
            transformation=exp_transformation,
            method_name="subtract",
            inputs=(6.0, 2.0),
            expected=np.float64(3.0),
            label="exp_subtract_becomes_divide",
        ),
        TestCase(
            transformation=exp_transformation,
            method_name="multiply",
            inputs=(2.0, 3.0),
            expected=np.exp(np.log(2.0) * np.log(3.0)),
            label="exp_multiply_two",
        ),
        TestCase(
            transformation=exp_transformation,
            method_name="divide",
            inputs=(8.0, 2.0),
            expected=np.exp(np.log(8.0) / np.log(2.0)),
            label="exp_divide",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="add",
            inputs=(np.array([1, 2, 3]), np.array([4, 5, 6])),
            expected=np.array([5, 7, 9]),
            label="identity_add_arrays",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="multiply",
            inputs=(
                np.array([2.0, 3.0]),
                np.array([4.0, 5.0]),
                np.array([6.0, 7.0]),
            ),
            expected=np.array([48.0, 105.0]),
            label="identity_multiply_three_arrays",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_arithmetic_methods(self, test_case: TestCase) -> None:
        method = getattr(test_case.transformation, test_case.method_name)
        result = method(*test_case.inputs)
        assert_array_equal(result, test_case.expected)


class TestTransformationCompose(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        transformation: Transformation
        other: Any
        inputs: Tuple[Any, ...]
        backward_inputs: Optional[Tuple[Any, ...]] = None
        expected_backward_result: Optional[Any] = None

    identity_transformation = Transformation(forward=identity, backward=identity)
    exp_transformation = Transformation(forward=exp, backward=np.log)
    square_transformation = Transformation(
        forward=lambda x: power(x, 2.0),
        backward=lambda x: power(x, 0.5),
    )

    test_cases = [
        TestCase(
            label="identity_compose_add",
            transformation=identity_transformation,
            other=np.add,
            inputs=(2, 3),
            expected=np.int64(5),
        ),
        TestCase(
            label="identity_compose_multiply",
            transformation=identity_transformation,
            other=np.multiply,
            inputs=(2, 3),
            expected=np.int64(6),
        ),
        TestCase(
            label="exp_compose_add",
            transformation=exp_transformation,
            other=np.add,
            inputs=(2.0, 3.0),
            expected=np.float64(6.0),
        ),
        TestCase(
            label="identity_compose_identity_transformation",
            transformation=identity_transformation,
            other=identity_transformation,
            inputs=(5,),
            expected=5,
            backward_inputs=(5,),
            expected_backward_result=5,
        ),
        TestCase(
            label="exp_compose_identity_transformation",
            transformation=exp_transformation,
            other=identity_transformation,
            inputs=(2.0,),
            expected=np.exp(2.0),
            backward_inputs=(1.0,),
            expected_backward_result=np.float64(0.0),
        ),
        TestCase(
            label="identity_compose_square_transformation",
            transformation=identity_transformation,
            other=square_transformation,
            inputs=(3.0,),
            expected=np.float64(9.0),
            backward_inputs=(9.0,),
            expected_backward_result=np.float64(3.0),
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_compose(self, test_case: TestCase) -> None:
        composed = test_case.transformation.compose(test_case.other)
        if isinstance(composed, Transformation):
            assert test_case.backward_inputs is not None
            assert test_case.expected_backward_result is not None
            result = composed.forward(*test_case.inputs)
            assert_array_equal(result, test_case.expected)
            backward_result = composed.backward(*test_case.backward_inputs)
            assert_array_equal(backward_result, test_case.expected_backward_result)
        else:
            result = composed(*test_case.inputs)
            assert_array_equal(result, test_case.expected)


class TestTransformationErrors(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Any
        transformation: Transformation
        method_name: str
        args: Tuple[Any, ...]
        kwargs: Dict[str, Any]

    identity_transformation = Transformation(forward=identity, backward=identity)

    test_cases = [
        TestCase(
            transformation=identity_transformation,
            method_name="reduce",
            args=(np.add,),
            kwargs={},
            expected=ValueError,
            label="reduce_no_arrays",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="compose_function",
            args=("not_callable",),
            kwargs={},
            expected=TypeError,
            label="compose_function_not_callable",
        ),
        TestCase(
            transformation=identity_transformation,
            method_name="compose_function",
            args=(42,),
            kwargs={},
            expected=TypeError,
            label="compose_function_int",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_errors(self, test_case: TestCase) -> None:
        method = getattr(test_case.transformation, test_case.method_name)
        if expect_error(method, test_case.expected, *test_case.args, **test_case.kwargs):
            return
