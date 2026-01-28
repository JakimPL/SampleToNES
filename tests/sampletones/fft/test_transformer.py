from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, Tuple, Type, Union
from unittest.mock import patch

import numpy as np
import pytest

from sampletones.fft.transformer import FFTTransformer
from sampletones.structures.histogram import Histogram
from sampletones.types.array import Array, ArrayClasses, MultaryTransformation, Numeric, NumericClasses
from sampletones.utils.transformations.morpher import PowerMorpher
from sampletones.utils.transformations.transformation import Transformation
from tests.sampletones.arrays import assert_array_equal
from tests.sampletones.errors import expect_error
from tests.sampletones.functions import compare_functions


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


class TestFromGamma:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        gamma: float
        sample_rate: int
        expected_transformation: Union[Transformation, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            gamma=0,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=0.0).transformation,
            test_id="gamma_0_flat_features",
        ),
        TestCase(
            gamma=25,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=0.25).transformation,
            test_id="gamma_25_sqrt",
        ),
        TestCase(
            gamma=50,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=0.5).transformation,
            test_id="gamma_50_identity",
        ),
        TestCase(
            gamma=75,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=0.75).transformation,
            test_id="gamma_75_square",
        ),
        TestCase(
            gamma=100,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=1.0).transformation,
            test_id="gamma_100_sharp_features",
        ),
        TestCase(
            gamma=25.5,
            sample_rate=44100,
            expected_transformation=PowerMorpher(gamma=0.255).transformation,
            test_id="gamma_25.5_decimal",
        ),
        TestCase(
            gamma=50,
            sample_rate=48000,
            expected_transformation=PowerMorpher(gamma=0.5).transformation,
            test_id="sample_rate_48000",
        ),
        TestCase(
            gamma=50,
            sample_rate=8000,
            expected_transformation=PowerMorpher(gamma=0.5).transformation,
            test_id="sample_rate_8000",
        ),
        TestCase(
            gamma=-10,
            sample_rate=44100,
            expected_transformation=ValueError,
            test_id="gamma_negative_error",
        ),
        TestCase(
            gamma=150,
            sample_rate=44100,
            expected_transformation=ValueError,
            test_id="gamma_above_100_error",
        ),
        TestCase(
            gamma=float("nan"),
            sample_rate=44100,
            expected_transformation=ValueError,
            test_id="gamma_nan_error",
        ),
        TestCase(
            gamma=float("inf"),
            sample_rate=44100,
            expected_transformation=ValueError,
            test_id="gamma_inf_error",
        ),
        TestCase(
            gamma=50,
            sample_rate=-44100,
            expected_transformation=ValueError,
            test_id="sample_rate_negative_error",
        ),
        TestCase(
            gamma=50,
            sample_rate=0,
            expected_transformation=ValueError,
            test_id="sample_rate_zero_error",
        ),
        TestCase(
            gamma=50,
            sample_rate=100,
            expected_transformation=ValueError,
            test_id="sample_rate_too_low_error",
        ),
        TestCase(
            gamma=50,
            sample_rate=1000000,
            expected_transformation=ValueError,
            test_id="sample_rate_too_high_error",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_from_gamma(self, test_case: TestCase) -> None:
        if not expect_error(
            FFTTransformer.from_gamma,
            test_case.expected_transformation,
            gamma=test_case.gamma,
            sample_rate=test_case.sample_rate,
            match=test_case.match,
        ):
            result = FFTTransformer.from_gamma(gamma=test_case.gamma, sample_rate=test_case.sample_rate)
            assert isinstance(result, FFTTransformer)
            assert result.sample_rate == test_case.sample_rate
            assert isinstance(test_case.expected_transformation, Transformation)
            assert compare_functions(result.transformation.forward, test_case.expected_transformation.forward)
            assert compare_functions(result.transformation.backward, test_case.expected_transformation.backward)

            test_value = np.array([4.0, 9.0, 16.0], dtype=np.float32)
            expected_forward = test_case.expected_transformation.forward(test_value)
            actual_forward = result.transformation.forward(test_value)
            assert_array_equal(actual_forward, expected_forward)

            expected_backward = test_case.expected_transformation.backward(expected_forward)
            actual_backward = result.transformation.backward(actual_forward)
            assert_array_equal(actual_backward, expected_backward)


class TestCalculateSpectrum:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: np.ndarray
        sample_rate: int
        fft_size: Optional[int]
        mock_spectrum: Histogram
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([0.0, 1000.0, 2000.0, 3000.0], dtype=np.float32),
                np.array([100.0, 200.0, 300.0], dtype=np.float32),
            ),
            expected_result=Histogram(
                np.array([0.0, 1000.0, 2000.0, 3000.0], dtype=np.float32),
                np.array([100.0, 200.0, 300.0], dtype=np.float32),
            ),
            test_id="valid_spectrum_default_fft_size",
        ),
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=8,
            mock_spectrum=Histogram(
                np.array([0.0, 500.0, 1000.0], dtype=np.float32),
                np.array([50.0, 100.0], dtype=np.float32),
            ),
            expected_result=Histogram(
                np.array([0.0, 500.0, 1000.0], dtype=np.float32),
                np.array([50.0, 100.0], dtype=np.float32),
            ),
            test_id="valid_spectrum_custom_fft_size",
        ),
        TestCase(
            audio=np.array([0.5, 0.6, 0.7], dtype=np.float32),
            sample_rate=22050,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([10.0, 20.0, 30.0], dtype=np.float32),
            ),
            expected_result=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([10.0, 20.0, 30.0], dtype=np.float32),
            ),
            test_id="valid_spectrum_log_bins",
        ),
        TestCase(
            audio=np.array([0.1, 0.2], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([0.0, 1000.0, 2000.0], dtype=np.float32),
                np.array([-10.0, 20.0], dtype=np.float32),
            ),
            expected_result=ValueError,
            match="negative values",
            test_id="spectrum_with_negative_values_error",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_calculate_spectrum(self, test_case: TestCase, transformer_identity: FFTTransformer) -> None:
        with patch("sampletones.fft.transformer.calculate_spectrum", return_value=test_case.mock_spectrum):
            if not expect_error(
                transformer_identity.calculate_spectrum,
                test_case.expected_result,
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
                assert isinstance(test_case.expected_result, Histogram)
                assert_array_equal(result.edges, test_case.expected_result.edges)
                assert_array_equal(result.values, test_case.expected_result.values)


class TestCalculateFeature:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        audio: np.ndarray
        sample_rate: int
        fft_size: Optional[int]
        mock_spectrum: Histogram
        transformer: TransformerFixture
        expected_result: Union[Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            test_id="identity_transformation_no_change",
        ),
        TestCase(
            audio=np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                np.array([4.0, 9.0, 16.0], dtype=np.float64),
            ),
            transformer=TransformerFixture.SQUARE,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                np.array([20.0, 30.0, 40.0], dtype=np.float64),
            ),
            test_id="square_transformation_sqrt_densities",
        ),
        TestCase(
            audio=np.array([0.5, 0.6], dtype=np.float32),
            sample_rate=22050,
            fft_size=4,
            mock_spectrum=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected_result=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            test_id="identity_log_bins",
        ),
        TestCase(
            audio=np.array([0.5, 0.6], dtype=np.float32),
            sample_rate=22050,
            fft_size=4,
            mock_spectrum=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([220.0, 440.0, 495.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.SQUARE,
            expected_result=Histogram(
                np.array([55.0, 110.0, 220.0, 440.0], dtype=np.float32),
                np.array([110.0, 220.0, 330.0], dtype=np.float32),
            ),
            test_id="square_log_bins",
        ),
        TestCase(
            audio=np.array([0.1, 0.2], dtype=np.float32),
            sample_rate=44100,
            fft_size=None,
            mock_spectrum=Histogram(
                np.array([0.0, 1000.0, 2000.0], dtype=np.float32),
                np.array([-10.0, 20.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected_result=ValueError,
            match="negative values",
            test_id="negative_spectrum_error",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_calculate_feature(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        with patch("sampletones.fft.transformer.calculate_spectrum", return_value=test_case.mock_spectrum):
            if not expect_error(
                transformer.calculate_feature,
                test_case.expected_result,
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
                assert isinstance(test_case.expected_result, Histogram)
                assert_array_equal(result.edges, test_case.expected_result.edges)
                assert_array_equal(result.values, test_case.expected_result.values)


class TestForward:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        input_data: Union[Numeric, Array, Histogram]
        transformer: TransformerFixture
        expected_result: Union[Numeric, Array, Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            input_data=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            test_id="identity_histogram_no_change",
        ),
        TestCase(
            input_data=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                np.array([4.0, 9.0, 16.0], dtype=np.float64),
            ),
            transformer=TransformerFixture.SQUARE,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float64),
                np.array([20.0, 30.0, 40.0], dtype=np.float64),
            ),
            test_id="square_histogram_sqrt_densities",
        ),
        TestCase(
            input_data=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            transformer=TransformerFixture.IDENTITY,
            expected_result=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            test_id="identity_array_no_change",
        ),
        TestCase(
            input_data=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            transformer=TransformerFixture.SQUARE,
            expected_result=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            test_id="square_array_sqrt_values",
        ),
        TestCase(
            input_data=4.0,
            transformer=TransformerFixture.IDENTITY,
            expected_result=4.0,
            test_id="identity_scalar_no_change",
        ),
        TestCase(
            input_data=16.0,
            transformer=TransformerFixture.SQUARE,
            expected_result=4.0,
            test_id="square_scalar_sqrt_value",
        ),
        TestCase(
            input_data="invalid",
            transformer=TransformerFixture.IDENTITY,
            expected_result=TypeError,
            match="must be a Histogram or Array/Numeric",
            test_id="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_forward(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.forward,
            test_case.expected_result,
            test_case.input_data,
            match=test_case.match,
        ):
            result = transformer.forward(test_case.input_data)

            if isinstance(test_case.expected_result, Histogram):
                assert isinstance(result, Histogram)
                assert_array_equal(result.edges, test_case.expected_result.edges)
                assert_array_equal(result.values, test_case.expected_result.values)
            elif isinstance(test_case.expected_result, ArrayClasses):
                assert isinstance(result, ArrayClasses)
                assert_array_equal(result, test_case.expected_result)
            elif isinstance(test_case.expected_result, NumericClasses):
                assert isinstance(result, NumericClasses)
                assert np.isclose(result, test_case.expected_result)
            else:
                pytest.fail("Unreachable code reached")


class TestBackward:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        input_data: Union[Numeric, Array, Histogram]
        transformer: TransformerFixture
        expected_result: Union[Array, Numeric, Histogram, Type[Exception]]
        match: Optional[str] = None

    test_cases = [
        TestCase(
            input_data=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.IDENTITY,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([4.0, 9.0, 16.0], dtype=np.float32),
            ),
            test_id="identity_histogram_no_change",
        ),
        TestCase(
            input_data=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([2.0, 3.0, 4.0], dtype=np.float32),
            ),
            transformer=TransformerFixture.SQUARE,
            expected_result=Histogram(
                np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                np.array([0.04, 0.09, 0.16], dtype=np.float32),
            ),
            test_id="square_histogram_square_densities",
        ),
        TestCase(
            input_data=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            transformer=TransformerFixture.IDENTITY,
            expected_result=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            test_id="identity_array_no_change",
        ),
        TestCase(
            input_data=np.array([1.0, 2.0, 3.0], dtype=np.float32),
            transformer=TransformerFixture.SQUARE,
            expected_result=np.array([1.0, 4.0, 9.0], dtype=np.float32),
            test_id="square_array_square_values",
        ),
        TestCase(
            input_data=16.0,
            transformer=TransformerFixture.IDENTITY,
            expected_result=16.0,
            test_id="identity_scalar_no_change",
        ),
        TestCase(
            input_data=4.0,
            transformer=TransformerFixture.SQUARE,
            expected_result=16.0,
            test_id="square_scalar_square_value",
        ),
        TestCase(
            input_data="invalid",
            transformer=TransformerFixture.IDENTITY,
            expected_result=TypeError,
            match="must be a Histogram or Array/Numeric",
            test_id="invalid_type_error",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_backward(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.backward,
            test_case.expected_result,
            test_case.input_data,
            match=test_case.match,
        ):
            result = transformer.backward(test_case.input_data)

            if isinstance(test_case.expected_result, Histogram):
                assert isinstance(result, Histogram)
                assert_array_equal(result.edges, test_case.expected_result.edges)
                assert_array_equal(result.values, test_case.expected_result.values)
            elif isinstance(test_case.expected_result, ArrayClasses):
                assert isinstance(result, ArrayClasses)
                assert_array_equal(result, test_case.expected_result)
            elif isinstance(test_case.expected_result, NumericClasses):
                assert isinstance(result, NumericClasses)
                assert np.isclose(result, test_case.expected_result)
            else:
                pytest.fail("Unreachable code reached")


class TestComposeFunction:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        transformer: TransformerFixture
        operation: MultaryTransformation[Union[Numeric, Array]]
        arguments: Tuple[Union[Numeric, Array], ...]
        expected_result: Union[float, Array]

    test_cases = [
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x: x * 2.0,
            arguments=(np.array([4.0, 9.0, 16.0], dtype=np.float32),),
            expected_result=np.array([8.0, 18.0, 32.0], dtype=np.float32),
            test_id="identity_unary_multiply_by_2",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=np.add,
            arguments=(
                np.array([1.0, 2.0, 3.0], dtype=np.float64),
                np.array([4.0, 5.0, 6.0], dtype=np.float64),
            ),
            expected_result=np.array([5.0, 7.0, 9.0], dtype=np.float64),
            test_id="identity_binary_add",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x, y, z: x + y + z,
            arguments=(
                np.array([1.0, 2.0], dtype=np.float32),
                np.array([3.0, 4.0], dtype=np.float32),
                np.array([5.0, 6.0], dtype=np.float32),
            ),
            expected_result=np.array([9.0, 12.0], dtype=np.float32),
            test_id="identity_ternary_sum",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.array([4.0, 6.0, 8.0], dtype=np.float64),),
            expected_result=np.array([8.0, 12.0, 16.0], dtype=np.float64),
            test_id="square_unary_multiply_by_4",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(
                np.array([3.0, 4.0], dtype=np.float32),
                np.array([4.0, 3.0], dtype=np.float32),
            ),
            expected_result=np.array([5.0, 5.0], dtype=np.float32),
            test_id="square_binary_add",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x, y, z: x + y + z,
            arguments=(
                np.array([3.0, 4.0, 12.0], dtype=np.float32),
                np.array([4.0, 3.0, 5.0], dtype=np.float32),
                np.array([12.0, 12.0, 0.0], dtype=np.float32),
            ),
            expected_result=np.array([13.0, 13.0, 13.0], dtype=np.float32),
            test_id="square_ternary_sum",
        ),
        TestCase(
            transformer=TransformerFixture.IDENTITY,
            operation=lambda x: x * 2.0,
            arguments=(9.0,),
            expected_result=18.0,
            test_id="identity_scalar_float",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.float32(3.0),),
            expected_result=np.float32(6.0),
            test_id="square_scalar_float32",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=lambda x: x * 4.0,
            arguments=(np.float64(4.0),),
            expected_result=np.float64(8.0),
            test_id="square_scalar_float64",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_compose_function(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)
        composed_function = transformer.compose_function(test_case.operation)
        result = composed_function(*test_case.arguments)

        if isinstance(test_case.expected_result, ArrayClasses):
            assert isinstance(result, ArrayClasses)
            assert_array_equal(result, test_case.expected_result)
        elif isinstance(test_case.expected_result, NumericClasses):
            assert isinstance(result, NumericClasses)
            assert np.isclose(result, test_case.expected_result)
        else:
            pytest.fail("Unreachable code reached")


class TestApply:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        transformer: TransformerFixture
        operation: MultaryTransformation
        arguments: Tuple[Histogram, ...]
        expected_result: Union[Histogram, Type[Exception]]

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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32), values=np.array([500.0, 500.0], dtype=np.float32)
            ),
            test_id="square_binary_add",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([1200.0, 1200.0], dtype=np.float64),
            ),
            test_id="square_binary_multiply",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([1300.0, 1300.0, 1300.0], dtype=np.float32),
            ),
            test_id="square_ternary_sum",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([14400.0, 14400.0], dtype=np.float64),
            ),
            test_id="square_ternary_multiply",
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
            expected_result=TypeError,
            test_id="non_callable_operation",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_apply(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.apply,
            test_case.expected_result,
            test_case.operation,
            *test_case.arguments,
        ):
            result = transformer.apply(test_case.operation, *test_case.arguments)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected_result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)


class TestReduce:
    @dataclass(frozen=True)
    class TestCase:
        __test__ = False

        test_id: str
        transformer: TransformerFixture
        operation: MultaryTransformation
        arguments: Tuple[Histogram, ...]
        expected_result: Union[Histogram, Type[Exception]]

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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32), values=np.array([500.0, 500.0], dtype=np.float32)
            ),
            test_id="square_add_two_arrays",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0, 300.0], dtype=np.float32),
                values=np.array([1300.0, 1300.0, 1300.0], dtype=np.float32),
            ),
            test_id="square_add_three_arrays",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float64),
                values=np.array([500.0, 500.0], dtype=np.float64),
            ),
            test_id="square_add_four_arrays",
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
            expected_result=Histogram(
                edges=np.array([0.0, 100.0, 200.0], dtype=np.float32),
                values=np.array([14400.0, 14400.0], dtype=np.float32),
            ),
            test_id="square_multiply_three_arrays",
        ),
        TestCase(
            transformer=TransformerFixture.SQUARE,
            operation=np.add,
            arguments=(),
            expected_result=ValueError,
            test_id="empty_arrays",
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda tc: tc.test_id)
    def test_reduce(self, test_case: TestCase, request: pytest.FixtureRequest) -> None:
        transformer = test_case.transformer.get_fixture(request)

        if not expect_error(
            transformer.reduce,
            test_case.expected_result,
            test_case.operation,
            *test_case.arguments,
        ):
            result = transformer.reduce(test_case.operation, *test_case.arguments)
            assert isinstance(result, Histogram)
            assert isinstance(test_case.expected_result, Histogram)
            assert_array_equal(result.edges, test_case.expected_result.edges)
            assert_array_equal(result.values, test_case.expected_result.values)
