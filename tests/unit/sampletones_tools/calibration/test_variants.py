import warnings
from dataclasses import dataclass
from typing import Dict, Final, List

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.enums import SelectorName, SpectrumMethod
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.config.settings import Overrides
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

METHODS: Final[List[SpectrumMethod]] = [SpectrumMethod.FFT, SpectrumMethod.CQT]
EXPONENTS: Final[List[float]] = [1.0]
DEFAULT_LEVEL: Final[List[VariantLevel]] = [VariantLevel.DEFAULT]
BOTH_LEVELS: Final[List[VariantLevel]] = [VariantLevel.DEFAULT, VariantLevel.TRUE]
GREEDY: Final[Overrides] = {"generation": {"decoder": {"selector": "greedy"}}}
NO_SETTINGS: Final[Dict[str, Overrides]] = {}


def _variants(
    methods: List[SpectrumMethod],
    exponents: List[float],
    temporal_weights: List[float],
) -> List[CalibrationVariant]:
    return build_variants(Config(), methods, exponents, temporal_weights, settings=NO_SETTINGS, levels=DEFAULT_LEVEL)


class TestSweepOrder(BaseTestSuite):
    """The sweep's order is the run's order: the report's rows and the page's columns follow it."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        methods: List[SpectrumMethod]
        exponents: List[float]
        temporal_weights: List[float]
        settings: Dict[str, Overrides]
        levels: List[VariantLevel]
        labels: List[str]

    test_cases = (
        TestCase(
            methods=METHODS,
            exponents=[1.0, 0.5],
            temporal_weights=[0.25],
            settings=NO_SETTINGS,
            levels=DEFAULT_LEVEL,
            labels=["fft-pe1-tw0.25", "fft-pe0.5-tw0.25", "cqt-pe1-tw0.25", "cqt-pe0.5-tw0.25"],
            label="methods_then_exponents",
        ),
        TestCase(
            methods=[SpectrumMethod.CQT],
            exponents=EXPONENTS,
            temporal_weights=[0.1, 0.3],
            settings={"greedy": GREEDY},
            levels=DEFAULT_LEVEL,
            labels=["cqt-pe1-tw0.1", "cqt-pe1-tw0.1-greedy", "cqt-pe1-tw0.3", "cqt-pe1-tw0.3-greedy"],
            label="weights_then_settings",
        ),
        TestCase(
            methods=[SpectrumMethod.CQT],
            exponents=EXPONENTS,
            temporal_weights=[],
            settings={"greedy": GREEDY},
            levels=BOTH_LEVELS,
            labels=["cqt-pe1", "cqt-pe1-true", "cqt-pe1-greedy", "cqt-pe1-greedy-true"],
            label="settings_then_levels",
        ),
        TestCase(
            methods=[SpectrumMethod.CQT],
            exponents=EXPONENTS,
            temporal_weights=[],
            settings=NO_SETTINGS,
            levels=[VariantLevel.TRUE, VariantLevel.DEFAULT],
            labels=["cqt-pe1-true", "cqt-pe1"],
            label="levels_in_the_order_named",
        ),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_the_last_part_of_the_sweep_varies_fastest(self, test_case: TestCase) -> None:
        variants = build_variants(
            Config(),
            test_case.methods,
            test_case.exponents,
            test_case.temporal_weights,
            settings=test_case.settings,
            levels=test_case.levels,
        )

        assert [variant.label for variant in variants] == test_case.labels


class TestBuildVariants:
    @pytest.mark.parametrize("method", METHODS, ids=lambda method: method.value)
    def test_variant_holds_the_spectrum_method_member(self, method: SpectrumMethod) -> None:
        (variant,) = _variants([method], EXPONENTS, [])
        assert variant.config.library.spectrum_method is method

    def test_a_variant_scores_at_its_perceptual_exponent(self) -> None:
        (variant,) = _variants([SpectrumMethod.CQT], [0.5], [])

        assert variant.config.generation.metric.perceptual_exponent == 0.5

    def test_a_swept_temporal_weight_leaves_the_spectral_weight_the_rest_of_the_blend(self) -> None:
        (variant,) = _variants([SpectrumMethod.CQT], EXPONENTS, [0.25])

        weights = variant.config.generation.weights
        assert (weights.temporal_loss_weight, weights.spectral_loss_weight) == (0.25, 0.75)

    def test_without_a_swept_temporal_weight_the_base_blend_stays(self) -> None:
        (variant,) = _variants([SpectrumMethod.CQT], EXPONENTS, [])

        assert variant.config.generation.weights == Config().generation.weights

    def test_variant_configuration_serializes_cleanly(self) -> None:
        variants = _variants(METHODS, EXPONENTS, [])
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            for variant in variants:
                variant.config.model_dump()

    def test_a_named_set_of_settings_is_measured_beside_the_base(self) -> None:
        variants = build_variants(
            Config(),
            [SpectrumMethod.CQT],
            EXPONENTS,
            [],
            settings={"greedy": GREEDY},
            levels=DEFAULT_LEVEL,
        )

        assert [variant.label for variant in variants] == ["cqt-pe1", "cqt-pe1-greedy"]
        assert [variant.config.generation.decoder.selector for variant in variants] == [
            Config().generation.decoder.selector,
            SelectorName.GREEDY,
        ]

    def test_a_set_of_settings_keeps_every_value_it_leaves_unnamed(self) -> None:
        base, greedy = build_variants(
            Config(),
            [SpectrumMethod.CQT],
            EXPONENTS,
            [],
            settings={"greedy": GREEDY},
            levels=DEFAULT_LEVEL,
        )

        assert greedy.config.generation.decoder.top_k == base.config.generation.decoder.top_k
        assert greedy.config.library == base.config.library

    def test_a_set_of_settings_is_written_over_the_swept_point(self) -> None:
        _, greedy = build_variants(
            Config(),
            [SpectrumMethod.FFT],
            [0.5],
            [],
            settings={"greedy": GREEDY},
            levels=DEFAULT_LEVEL,
        )

        assert greedy.config.library.spectrum_method is SpectrumMethod.FFT
        assert greedy.config.generation.metric.perceptual_exponent == 0.5

    def test_a_set_naming_a_setting_the_configuration_lacks_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            build_variants(
                Config(),
                [SpectrumMethod.CQT],
                EXPONENTS,
                [],
                settings={"typo": {"generation": {"decoder": {"selektor": "greedy"}}}},
                levels=DEFAULT_LEVEL,
            )

    def test_the_true_level_reads_files_unnormalized_under_a_label_of_its_own(self) -> None:
        default, true = build_variants(
            Config(),
            [SpectrumMethod.CQT],
            EXPONENTS,
            [],
            settings=NO_SETTINGS,
            levels=BOTH_LEVELS,
        )

        assert (default.label, true.label) == ("cqt-pe1", "cqt-pe1-true")
        assert (default.level, true.level) == (VariantLevel.DEFAULT, VariantLevel.TRUE)
        assert default.config.general.normalize == Config().general.normalize
        assert true.config.general.normalize is False

    def test_an_empty_sweep_leaves_no_variant(self) -> None:
        assert not _variants([], EXPONENTS, [])


class TestSharedLabels(BaseTestSuite):
    """A label names one variant, so a sweep spelling two points alike is refused, naming the label."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        methods: List[SpectrumMethod]
        exponents: List[float]
        shared: str

    test_cases = (
        TestCase(methods=[SpectrumMethod.CQT, SpectrumMethod.CQT], exponents=[1.0], shared="cqt-pe1", label="method"),
        TestCase(methods=[SpectrumMethod.FFT], exponents=[0.5, 0.5000001], shared="fft-pe0.5", label="exponent"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_two_points_spelled_alike_are_refused_naming_the_label(self, test_case: TestCase) -> None:
        with pytest.raises(ValueError, match=f"named {test_case.shared};"):
            _variants(test_case.methods, test_case.exponents, [])

    def test_exponents_spelled_apart_are_measured_apart(self) -> None:
        labels = [variant.label for variant in _variants([SpectrumMethod.FFT], [0.5, 0.75], [])]

        assert labels == ["fft-pe0.5", "fft-pe0.75"]
