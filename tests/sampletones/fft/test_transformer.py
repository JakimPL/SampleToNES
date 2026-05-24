from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Tuple, Type, Union
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_core.fft.transformer import FFTTransformer
from sampletones_core.structures.histogram import Histogram
from sampletones_shared.types.array import Array, ArrayClasses, MultaryTransformation, Numeric, NumericClasses
from sampletones_shared.utils.transformations.morpher import PowerMorpher
from sampletones_shared.utils.transformations.transformation import Transformation
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error
from tests.sampletones.functions import compare_functions
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@pytest.fixture
def transformer_identity() -> FFTTransformer:
    """FFTTransformer with gamma=50 (identity transformation, a=1.0)."""
    return FFTTransformer.from_gamma(gamma=50, sample_rate=44100)


@pytest.fixture
def transformer_square() -> FFTTransformer:
    """FFTTransformer with gamma=25 (a=0.5, sqrt transformation)."""
    return FFTTransformer.from_gamma(gamma=25, sample_rate=44100)


class TransformerFixture(StrEnum):
    """Enum for selecting transformer fixtures."""

    IDENTITY = "identity"
    SQUARE = "square"

    def get_fixture(self, request: pytest.FixtureRequest) -> FFTTransformer:
        """Get the transformer fixture."""
        return request.getfixturevalue(f"transformer_{self.value}")


class TestFromGamma(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Transformation, Type[Exception]]
        gamma: Union[int, float]
        sample_rate: int
        match: Optional[str] = None

    test_cases = [
        TestCase(
            label="gamma_0_flat_features",
            gamma=0,
            sample_rate=44100,
            expected=PowerMorpher(gamma=0.0).transformation,
        ),
        TestCase(
            label="gamma_25_sqrt",
            gamma=25,
            sample_rate=44100,
            expected=PowerMorpher(gamma=0.25).transformation,
        ),
        TestCase(
            label="gamma_50_identity",
            gamma=50,
            sample_rate=44100,
            expected=PowerMorpher(gamma=0.5).transformation,
        ),
        TestCase(
            label="gamma_75_square",
            gamma=75,
            sample_rate=44100,
            expected=PowerMorpher(gamma=0.75).transformation,
        ),
        TestCase(
            label="gamma_100_sharp_features",
            gamma=100,
            sample_rate=44100,
            expected=PowerMorpher(gamma=1.0).transformation,
        ),
        TestCase(
            label="gamma_25.5_decimal",
            gamma=25.5,
            sample_rate=44100,
            expected=PowerMorpher(gamma=0.255).transformation,
        ),
        TestCase(
            label="sample_rate_48000",
            gamma=50,
            sample_rate=48000,
            expected=PowerMorpher(gamma=0.5).transformation,
        ),
        TestCase(
            label="sample_rate_8000",
            gamma=50,
            sample_rate=8000,
            expected=PowerMorpher(gamma=0.5).transformation,
        ),
        TestCase(
            label="gamma_negative_error",
            gamma=-10,
            sample_rate=44100,
            expected=ValueError,
        ),
        TestCase(
            label="gamma_above_100_error",
            gamma=150,
            sample_rate=44100,
            expected=ValueError,
        ),
        TestCase(
            label="gamma_nan_error",
            gamma=float("nan"),
            sample_rate=44100,
            expected=ValueError,
        ),
        TestCase(
            label="gamma_inf_error",
            gamma=float("inf"),
            sample_rate=44100,
            expected=ValueError,
        ),
        TestCase(
            label="sample_rate_negative_error",
            gamma=50,
            sample_rate=-44100,
            expected=ValueError,
        ),
        TestCase(
            label="sample_rate_zero_error",
            gamma=50,
            sample_rate=0,
            expected=ValueError,
        ),
        TestCase(
            label="sample_rate_too_low_error",
            gamma=50,
            sample_rate=100,
            expected=ValueError,
        ),
        TestCase(
            label="sample_rate_too_high_error",
            gamma=50,
            sample_rate=1000000,
            expected=ValueError,
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_from_gamma(self, test_case: TestCase) -> None:
        if not expect_error(
            FFTTransformer.from_gamma,
            test_case.expected,
            gamma=test_case.gamma,
            sample_rate=test_case.sample_rate,
            match=test_case.match,
        ):
            result = FFTTransformer.from_gamma(gamma=test_case.gamma, sample_rate=test_case.sample_rate)
            assert isinstance(result, FFTTransformer)
            assert result.sample_rate == test_case.sample_rate
            assert isinstance(test_case.expected, Transformation)
            assert compare_functions(result.transformation.forward, test_case.expected.forward)
            assert compare_functions(result.transformation.backward, test_case.expected.backward)

            test_value = np.array([4.0, 9.0, 16.0], dtype=np.float32)
            expected_forward = test_case.expected.forward(test_value)
            actual_forward = result.transformation.forward(test_value)
            assert_array_equal(actual_forward, expected_forward)

            expected_backward = test_case.expected.backward(expected_forward)
            actual_backward = result.transformation.backward(actual_forward)
            assert_array_equal(actual_backward, expected_backward)


class TestCalculateSpectrum(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        audio: np.ndarray
        sample_rate: int
        fft_size: Optional[int]
        mock_spectrum: Histogram
        match: Optional[str] = None

    test_cases = [
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 1000.0, 2000.0, 3000.0], dtype=np.float32),
                values=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            ),
            expected=Histogram(
                edges=np.array([0.0, 1000.0, 2000.0, 3000.0], dtype=np.float32),
                values=np.array([100.0, 200.0, 300.0], dtype=np.float32),
            ),
            label="valid_spectrum_default_fft_size",
        ),
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=8,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 500.0, 1000.0], dtype=np.float32), values=np.array([50.0, 100.0], dtype=np.float32)
            ),
            expected=Histogram(
                edges=np.array([0.0, 500.0, 1000.0], dtype=np.float32), values=np.array([50.0, 100.0], dtype=np.float32)
            ),
            label="valid_spectrum_custom_fft_size",
        ),
        TestCase(
            audio=np.array([0.5, 0.6, 0.7], dtype=np.float32),
            sample_rate=22050,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([10.0, 20.0, 30.0], dtype=np.float32),
            ),
            expected=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([10.0, 20.0, 30.0], dtype=np.float32),
            ),
            label="valid_spectrum_log_bins",
        ),
        TestCase(
            audio=np.array([0.1, 0.2], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 1000.0, 2000.0], dtype=np.float32),
                values=np.array([-10.0, 20.0], dtype=np.float32),
            ),
            expected=ValueError,
            match="negative values",
            label="spectrum_with_negative_values_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_calculate_spectrum(self, test_case: TestCase, transformer_identity: FFTTransformer) -> None:
        with patch("sampletones_core.fft.transformer.calculate_spectrum", return_value=test_case.mock_spectrum):
            if not expect_error(
                transformer_identity.calculate_spectrum,
                test_case.expected,
                test_case.audio,
                test_case.sample_rate,
                test_case.fft_size,
                match=test_case.match,
            ):
                result = transformer_identity.calculate_spectrum(
                    test_case.audio,
                    test_case.sample_rate,
                    test_case.fft_size,
                )
                assert isinstance(result, Histogram)
                assert isinstance(test_case.expected, Histogram)
                assert_array_equal(result.edges, test_case.expected.edges)
                assert_array_equal(result.values, test_case.expected.values)


class TestCalculateFeature(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        audio: np.ndarray
        sample_rate: int
        fft_size: Optional[int]
        mock_spectrum: Histogram
        transformer: TransformerFixture
        match: Optional[str] = None

    test_cases = [
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            label="identity_transformation_no_change",
        ),
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float64),
            ),
            transformer=TransformerFixture.SQUARE,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                values=np.array([20.0, 30.0, 40.0], dtype=np.float64),
            ),
            label="square_transformation_sqrt_densities",
        ),
        TestCase(
            audio=np.array([0.5, 0.6], dtype=np.float32),
            sample_rate=22050,
            fft_size=4,
            mock_spectrum=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            label="identity_log_bins",
        ),
        TestCase(
            audio=np.array([0.5, 0.6], dtype=np.float32),
            sample_rate=22050,
            fft_size=4,
            mock_spectrum=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([220.0, 440.0, 495.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.SQUARE,
            expected=Histogram(
                edges=np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                values=np.array([110.0, 220.0, 330.0], dtype=np.float32),
            ),
            label="square_log_bins",
        ),
        TestCase(
            audio=np.array([0.1, 0.2], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                edges=np.array([0.0, 1000.0, 2000.0], dtype=np.float32),
                values=np.array([-10.0, 20.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected=ValueError,
            match="negative values",
            label="negative_spectrum_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_calculate_feature(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        with patch("sampletones_core.fft.transformer.calculate_spectrum", return_value=test_case.mock_spectrum):
            if not expect_error(
                transformer.calculate_feature,
                test_case.expected,
                test_case.audio,
                test_case.sample_rate,
                test_case.fft_size,
                match=test_case.match,
            ):
                result = transformer.calculate_feature(
                    test_case.audio,
                    test_case.sample_rate,
                    test_case.fft_size,
                )
                assert isinstance(result, Histogram)
                assert isinstance(test_case.expected, Histogram)
                assert_array_equal(result.edges, test_case.expected.edges)
                assert_array_equal(result.values, test_case.expected.values)


class TestForward(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Numeric, Array, Histogram, Type[Exception]]
        input_data: Union[Numeric, Array, Histogram]
        transformer: TransformerFixture
        match: Optional[str] = None

    test_cases = [
        TestCase(
            input_data=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            label="identity_histogram_no_change",
        ),
        TestCase(
            input_data=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float64),
            ),
            transformer=TransformerFixture.SQUARE,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                values=np.array([20.0, 30.0, 40.0], dtype=np.float64),
            ),
            label="square_histogram_sqrt_densities",
        ),
        TestCase(
            input_data=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            transformer=TransformerFixture.IDENTITY,
            expected=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            label="identity_array_no_change",
        ),
        TestCase(
            input_data=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            transformer=TransformerFixture.SQUARE,
            expected=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            label="square_array_sqrt_values",
        ),
        TestCase(
            input_data=4.0,
            transformer=TransformerFixture.IDENTITY,
            expected=4.0,
            label="identity_scalar_no_change",
        ),
        TestCase(
            input_data=16.0,
            transformer=TransformerFixture.SQUARE,
            expected=4.0,
            label="square_scalar_sqrt_value",
        ),
        TestCase(
            input_data="invalid",
            transformer=TransformerFixture.IDENTITY,
            expected=TypeError,
            match="must be a Histogram or Array/Numeric",
            label="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_forward(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.forward,
            test_case.expected,
            test_case.input_data,
            match=test_case.match,
        ):
            result = transformer.forward(test_case.input_data)

            if isinstance(test_case.expected, Histogram):
                assert isinstance(result, Histogram)
                assert_array_equal(result.edges, test_case.expected.edges)
                assert_array_equal(result.values, test_case.expected.values)
            elif isinstance(test_case.expected, ArrayClasses):
                assert isinstance(result, ArrayClasses)
                assert_array_equal(result, test_case.expected)
            elif isinstance(test_case.expected, NumericClasses):
                assert isinstance(result, NumericClasses)
                assert np.isclose(result, test_case.expected)
            else:
                pytest.fail("Unreachable code reached")


class TestBackward(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Array, Numeric, Histogram, Type[Exception]]
        input_data: Union[Numeric, Array, Histogram]
        transformer: TransformerFixture
        match: Optional[str] = None

    test_cases = [
        TestCase(
            input_data=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            label="identity_histogram_no_change",
        ),
        TestCase(
            input_data=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([2.0, 3.0, 4.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.SQUARE,
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([0.04, 0.09, 0.16], dtype=np.float32),
            ),
            label="square_histogram_square_densities",
        ),
        TestCase(
            input_data=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            transformer=TransformerFixture.IDENTITY,
            expected=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            label="identity_array_no_change",
        ),
        TestCase(
            input_data=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            transformer=TransformerFixture.SQUARE,
            expected=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            label="square_array_square_values",
        ),
        TestCase(
            input_data=16.0,
            transformer=TransformerFixture.IDENTITY,
            expected=16.0,
            label="identity_scalar_no_change",
        ),
        TestCase(
            input_data=4.0,
            transformer=TransformerFixture.SQUARE,
            expected=16.0,
            label="square_scalar_square_value",
        ),
        TestCase(
            input_data="invalid",
            transformer=TransformerFixture.IDENTITY,
            expected=TypeError,
            match="must be a Histogram or Array/Numeric",
            label="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_backward(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.backward,
            test_case.expected,
            test_case.input_data,
            match=test_case.match,
        ):
            result = transformer.backward(test_case.input_data)

            if isinstance(test_case.expected, Histogram):
                assert isinstance(result, Histogram)
                assert_array_equal(result.edges, test_case.expected.edges)
                assert_array_equal(result.values, test_case.expected.values)
            elif isinstance(test_case.expected, ArrayClasses):
                assert isinstance(result, ArrayClasses)
                assert_array_equal(result, test_case.expected)
            elif isinstance(test_case.expected, NumericClasses):
                assert isinstance(result, NumericClasses)
                assert np.isclose(result, test_case.expected)
            else:
                pytest.fail("Unreachable code reached")


class TestComposeFunction(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[float, Array]
        transformer: TransformerFixture
        operation: MultaryTransformation[Union[Numeric, Array]]
        arguments: Tuple[Union[Numeric, Array], ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x: x * 2.0,
            arguments=(np.array([4.0, 9.0, 16.0], dtype=np.float32),),
            expected=np.array([8.0, 18.0, 32.0], dtype=np.float32),
            label="identity_unary_multiply_by_2",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=np.add,
            arguments=(
                np.array([1.0, 2.0, 3.0], dtype=np.float64),
                np.array([4.0, 5.0, 6.0], dtype=np.float64),
            ),
            expected=np.array([5.0, 7.0, 9.0], dtype=np.float64),
            label="identity_binary_add",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x, y, z: x + y + z,
            arguments=(
                np.array([1.0, 2.0], dtype=np.float32),
                np.array([3.0, 4.0], dtype=np.float32),
                np.array([5.0, 6.0], dtype=np.float32),
            ),
            expected=np.array([9.0, 12.0], dtype=np.float32),
            label="identity_ternary_sum",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.array([4.0, 6.0, 8.0], dtype=np.float64),),
            expected=np.array([8.0, 12.0, 16.0], dtype=np.float64),
            label="square_unary_multiply_by_4",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                np.array([3.0, 4.0], dtype=np.float32),
                np.array([4.0, 3.0], dtype=np.float32),
            ),
            expected=np.array([5.0, 5.0], dtype=np.float32),
            label="square_binary_add",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x, y, z: x + y + z,
            arguments=(
                np.array([3.0, 4.0, 12.0], dtype=np.float32),
                np.array([4.0, 3.0, 5.0], dtype=np.float32),
                np.array([12.0, 12.0, 0.0], dtype=np.float32),
            ),
            expected=np.array([13.0, 13.0, 13.0], dtype=np.float32),
            label="square_ternary_sum",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x: x * 2.0,
            arguments=(9.0,),
            expected=18.0,
            label="identity_scalar_float",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.float32(3.0),),
            expected=np.float32(6.0),
            label="square_scalar_float32",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.float64(4.0),),
            expected=np.float64(8.0),
            label="square_scalar_float64",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_compose_function(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)
        composed_function = transformer.compose_function(test_case.operation)
        result = composed_function(*test_case.arguments)

        if isinstance(test_case.expected, ArrayClasses):
            assert isinstance(result, ArrayClasses)
            assert_array_equal(result, test_case.expected)
        elif isinstance(test_case.expected, NumericClasses):
            assert isinstance(result, NumericClasses)
            assert np.isclose(result, test_case.expected)
        else:
            pytest.fail("Unreachable code reached")


class TestApply(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        operation: MultaryTransformation
        arguments: Tuple[Histogram, ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 300.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32), values=np.array([500.0, 500.0], dtype=np.float32)
            ),
            label="square_binary_add",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.multiply,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 400.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 300.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([1200.0, 1200.0], dtype=np.float64),
            ),
            label="square_binary_multiply",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x, y, z: x + y + z,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([300.0, 400.0, 1200.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 300.0, 500.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([1200.0, 1200.0, 0.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([1300.0, 1300.0, 1300.0], dtype=np.float32),
            ),
            label="square_ternary_sum",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x, y, z: x * y * z,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 900.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([900.0, 400.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 400.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([14400.0, 14400.0], dtype=np.float64),
            ),
            label="square_ternary_multiply",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.float32(5.0),
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([100.0, 400.0], dtype=np.float32),
                ),
            ),
            expected=TypeError,
            label="non_callable_operation",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
            expected=TypeError,
            label="non_histogram_feature",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_apply(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.apply,
            test_case.expected,
            test_case.operation,
            *test_case.arguments,
        ):
            result = transformer.apply(test_case.operation, *test_case.arguments)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestReduce(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        operation: MultaryTransformation
        arguments: Tuple[Histogram, ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 300.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32), values=np.array([500.0, 500.0], dtype=np.float32)
            ),
            label="square_add_two_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([300.0, 400.0, 1200.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 300.0, 500.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([1200.0, 1200.0, 0.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([1300.0, 1300.0, 1300.0], dtype=np.float32),
            ),
            label="square_add_three_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([0.0, 300.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 0.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 0.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([0.0, 400.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([500.0, 500.0], dtype=np.float64),
            ),
            label="square_add_four_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.multiply,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([900.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 400.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                values=np.array([14400.0, 14400.0], dtype=np.float32),
            ),
            label="square_multiply_three_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(),
            expected=ValueError,
            label="empty_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                np.array([1.0, 2.0], dtype=np.float32),
            ),
            expected=TypeError,
            label="non_histogram_feature",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_reduce(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.reduce,
            test_case.expected,
            test_case.operation,
            *test_case.arguments,
        ):
            result = transformer.reduce(test_case.operation, *test_case.arguments)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestToFeatures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Tuple[Histogram, ...], Type[Exception]]
        transformer: TransformerFixture
        inputs: Tuple[Union[Histogram, Numeric], ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
            ),
            label="one_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 400.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 300.0], dtype=np.float64),
                ),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 400.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 300.0], dtype=np.float64),
                ),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                np.float32(4.0),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([200.0, 200.0], dtype=np.float32),
                ),
            ),
            label="histogram_then_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                np.float64(9.0),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 900.0], dtype=np.float64),
                ),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 300.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([400.0, 900.0], dtype=np.float64),
                ),
            ),
            label="scalar_then_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([100.0, 400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 900.0, 100.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([900.0, 100.0, 400.0], dtype=np.float32),
                ),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([100.0, 400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 900.0, 100.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([900.0, 100.0, 400.0], dtype=np.float32),
                ),
            ),
            label="three_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                np.float32(16.0),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                np.float32(9.0),
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 300.0], dtype=np.float32),
                ),
            ),
            label="scalar_histogram_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            inputs=(
                5.0,
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 700.0], dtype=np.float64),
                ),
                3.0,
            ),
            expected=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([500.0, 500.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 700.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([300.0, 300.0], dtype=np.float64),
                ),
            ),
            label="identity_scalar_histogram_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(np.float32(2.0), np.float32(3.0)),
            expected=TypeError,
            label="no_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                "invalid",
            ),
            expected=TypeError,
            label="invalid_type",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 500.0], dtype=np.float32),
                ),
            ),
            expected=ValueError,
            label="inconsistent_edges",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_to_features(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.to_features,
            test_case.expected,
            test_case.inputs,
        ):
            result = transformer.to_features(test_case.inputs)
            assert isinstance(test_case.expected, tuple)
            assert isinstance(result, list)
            assert len(result) == len(test_case.expected)

            for result_histogram, expected_histogram in zip(result, test_case.expected):
                assert isinstance(result_histogram, Histogram)
                assert isinstance(expected_histogram, Histogram)
                assert_array_equal(result_histogram.edges, expected_histogram.edges)
                assert_array_equal(result_histogram.values, expected_histogram.values)


class TestAdd(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        inputs: Tuple[Union[Histogram, Numeric], ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            label="single_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                    values=np.array([3.0, 4.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                    values=np.array([4.0, 3.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([5.0, 5.0], dtype=np.float64),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                    values=np.array([3.0, 0.0], dtype=np.float32),
                ),
                np.float32(16.0) / np.square(110.0, dtype=np.float32),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([5.0, 4.0], dtype=np.float32),
            ),
            label="histogram_plus_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                np.float64(9.0) / np.square(110.0, dtype=np.float64),
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                    values=np.array([4.0, 0.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([5.0, 3.0], dtype=np.float64),
            ),
            label="scalar_plus_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0, 385.0], dtype=np.float32),
                    values=np.array([3.0, 4.0, 12.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0, 385.0], dtype=np.float32),
                    values=np.array([4.0, 3.0, 5.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0, 385.0], dtype=np.float32),
                    values=np.array([12.0, 12.0, 0.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0, 385.0], dtype=np.float32),
                values=np.array([13.0, 13.0, 13.0], dtype=np.float32),
            ),
            label="three_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            inputs=(
                np.float64(3.0) / 110.0,
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                    values=np.array([500.0, 700.0], dtype=np.float64),
                ),
                np.float64(5.0) / 110.0,
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([508.0, 708.0], dtype=np.float64),
            ),
            label="scalar_histogram_scalar_identity",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(),
            expected=TypeError,
            label="empty_inputs",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                "invalid",
            ),
            expected=TypeError,
            label="invalid_type",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
            ),
            expected=ValueError,
            label="inconsistent_edges",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_add(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.add,
            test_case.expected,
            *test_case.inputs,
        ):
            result = transformer.add(*test_case.inputs)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestSubtract(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        input1: Union[Histogram, Numeric]
        input2: Union[Histogram, Numeric]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([5.0, 5.0], dtype=np.float32),
            ),
            input2=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([3.0, 4.0], dtype=np.float32),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([4.0, 3.0], dtype=np.float32),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([13.0, 4.0], dtype=np.float64),
            ),
            input2=np.float64(25.0) / np.square(110.0, dtype=np.float64),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([12.0, 3.0], dtype=np.float64),
            ),
            label="histogram_minus_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=np.float32(25.0) / np.square(110.0, dtype=np.float32),
            input2=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([3.0, 4.0], dtype=np.float32),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([4.0, 3.0], dtype=np.float32),
            ),
            label="scalar_minus_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([12.0, 13.0], dtype=np.float64),
            ),
            input2=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([13.0, 12.0], dtype=np.float64),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([5.0, 5.0], dtype=np.float64),
            ),
            label="negative_without_abs",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            input1=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([800.0, 500.0], dtype=np.float64),
            ),
            input2=np.float64(3.0),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([470.0, 170.0], dtype=np.float64),
            ),
            label="identity_histogram_minus_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            input2="invalid",
            expected=TypeError,
            label="invalid_type",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            input2=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            expected=ValueError,
            label="inconsistent_edges",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_subtract(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.subtract,
            test_case.expected,
            test_case.input1,
            test_case.input2,
        ):
            result = transformer.subtract(test_case.input1, test_case.input2)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestMultiply(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        inputs: Tuple[Union[Histogram, Numeric], ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            label="single_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([20.0, 40.0, 80.0], dtype=np.float64),
                    values=np.array([3.0, 4.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([20.0, 40.0, 80.0], dtype=np.float64),
                    values=np.array([4.0, 3.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([20.0, 40.0, 80.0], dtype=np.float64),
                values=np.array([0.6, 0.3], dtype=np.float64),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                    values=np.array([3.0, 4.0], dtype=np.float32),
                ),
                np.float32(4.0),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([6.0, 8.0], dtype=np.float32),
            ),
            label="histogram_times_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([0.0, 1.0, 5.0, 21.0], dtype=np.float32),
                    values=np.array([3.0, 4.0, 6.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 1.0, 5.0, 21.0], dtype=np.float32),
                    values=np.array([4.0, 6.0, 8.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 1.0, 5.0, 21.0], dtype=np.float32),
                    values=np.array([2.0, 5.0, 4.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 1.0, 5.0, 21.0], dtype=np.float32),
                values=np.array([24.0, 7.5, 0.75], dtype=np.float32),
            ),
            label="three_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            inputs=(
                np.float32(3.0),
                Histogram(
                    edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                    values=np.array([300.0, 500.0], dtype=np.float32),
                ),
                np.float32(2.0),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([1800.0, 3000.0], dtype=np.float32),
            ),
            label="scalar_histogram_scalar_identity",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(),
            expected=TypeError,
            label="empty_inputs",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            inputs=(
                Histogram(
                    edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                    values=np.array([400.0, 900.0], dtype=np.float32),
                ),
                [1, 2, 3],
            ),
            expected=TypeError,
            label="invalid_type",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_multiply(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.multiply,
            test_case.expected,
            *test_case.inputs,
        ):
            result = transformer.multiply(*test_case.inputs)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestDivide(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        input1: Union[Histogram, Numeric]
        input2: Union[Histogram, Numeric]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([12.0, 12.0], dtype=np.float64),
            ),
            input2=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([4.0, 3.0], dtype=np.float64),
            ),
            expected=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float64),
                values=np.array([330.0, 440.0], dtype=np.float64),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([12.0, 36.0], dtype=np.float64),
            ),
            input2=np.float64(9.0),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([4.0, 12.0], dtype=np.float64),
            ),
            label="histogram_divided_by_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=np.float64(144.0) / np.square(110.0, dtype=np.float64),
            input2=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([4.0, 3.0], dtype=np.float64),
            ),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([330.0, 440.0], dtype=np.float64),
            ),
            label="scalar_divided_by_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            input1=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([800.0, 1200.0], dtype=np.float64),
            ),
            input2=np.float64(4.0),
            expected=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float64),
                values=np.array([200.0, 300.0], dtype=np.float64),
            ),
            label="identity_histogram_divided_by_scalar",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            input2=np.array([1, 2]),
            expected=TypeError,
            label="invalid_type",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            input1=Histogram(
                edges=np.array([55.0, 165.0, 275.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            input2=Histogram(
                edges=np.array([110.0, 220.0, 330.0], dtype=np.float32),
                values=np.array([400.0, 900.0], dtype=np.float32),
            ),
            expected=ValueError,
            label="inconsistent_edges",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_divide(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.divide,
            test_case.expected,
            test_case.input1,
            test_case.input2,
        ):
            result = transformer.divide(test_case.input1, test_case.input2)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)


class TestMean(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expected: Union[Histogram, Type[Exception]]
        transformer: TransformerFixture
        features: Tuple[Histogram, ...]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.SQUARE,
            features=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                values=np.array([300.0, 400.0], dtype=np.float32),
            ),
            label="single_histogram",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            features=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([7.0, 17.0], dtype=np.float64),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                    values=np.array([1.0, 7.0], dtype=np.float64),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([5.0, 13.0], dtype=np.float64),
            ),
            label="two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            features=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([0.0, 1.0, 2.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([0.0, 1.0, 2.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                    values=np.array([0.0, 1.0, 2.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([0.0, 1.0, 2.0], dtype=np.float32),
            ),
            label="three_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            features=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 500.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([400.0, 300.0], dtype=np.float32),
                ),
            ),
            expected=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                values=np.array([350.0, 400.0], dtype=np.float32),
            ),
            label="identity_two_histograms",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            features=(),
            expected=ValueError,
            label="empty_features",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            features=(
                Histogram(
                    edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                    values=np.array([300.0, 400.0], dtype=np.float32),
                ),
                Histogram(
                    edges=np.array([0.0, 100.0, 300.0], dtype=np.float32),
                    values=np.array([400.0, 500.0], dtype=np.float32),
                ),
            ),
            expected=ValueError,
            label="inconsistent_edges",
        ),
    ]

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_mean(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.mean,
            test_case.expected,
            test_case.features,
        ):
            result = transformer.mean(test_case.features)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected, Histogram)
            assert_array_equal(result.edges, test_case.expected.edges)
            assert_array_equal(result.values, test_case.expected.values)
            assert_array_equal(result.values, test_case.expected.values)
