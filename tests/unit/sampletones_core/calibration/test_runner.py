import warnings
from typing import Final, List

import pytest

from sampletones_core.calibration.runner import build_variants
from sampletones_core.configs import Config
from sampletones_core.constants.enums import SpectrumMethod

METHODS: Final[List[SpectrumMethod]] = [SpectrumMethod.FFT, SpectrumMethod.CQT]
EXPONENTS: Final[List[float]] = [1.0]


class TestBuildVariants:
    def test_sweeps_every_combination(self) -> None:
        variants = build_variants(Config(), METHODS, [1.0, 0.5], [0.25])
        assert [variant.label for variant in variants] == [
            "fft-pe1-tw0.25",
            "fft-pe0.5-tw0.25",
            "cqt-pe1-tw0.25",
            "cqt-pe0.5-tw0.25",
        ]

    @pytest.mark.parametrize("method", METHODS, ids=lambda method: method.value)
    def test_variant_holds_the_spectrum_method_member(self, method: SpectrumMethod) -> None:
        (variant,) = build_variants(Config(), [method], EXPONENTS, [])
        assert variant.config.library.spectrum_method is method

    def test_variant_configuration_serializes_cleanly(self) -> None:
        variants = build_variants(Config(), METHODS, EXPONENTS, [])
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            for variant in variants:
                variant.config.model_dump()
