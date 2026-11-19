import warnings
from pathlib import Path
from typing import Final, List, cast

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.reconstructions import Reconstructor
from sampletones_tools.calibration.renders import read_record
from sampletones_tools.calibration.runner import Conversion, build_variants, evaluate_conversion, recorded_rows

from .conversions import WrittenReconstructor, item_named, stub_panel

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


class TestEvaluateConversion:
    def test_the_rows_returned_are_the_ones_the_record_keeps(self, tmp_path: Path) -> None:
        (variant,) = build_variants(Config(), [SpectrumMethod.FFT], EXPONENTS, [])
        item = item_named("a", listed=False)
        conversion = Conversion(
            variant=variant,
            item=item,
            position=0,
            paths=(tmp_path / "a",),
            stems=None,
            channels=frozenset({ChannelName.PULSE1}),
            run_directory=tmp_path,
        )

        rows = evaluate_conversion(conversion, cast(Reconstructor, WrittenReconstructor()), stub_panel())

        record = read_record(tmp_path, variant.label, item.name)
        assert record is not None
        assert [row.referee for row in rows] == ["stub"]
        assert rows == recorded_rows(record)
