import warnings
from pathlib import Path
from typing import AbstractSet, Final, FrozenSet, List, Optional

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.types.path import Pathlike
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.runner import build_variants, evaluate_variants

METHODS: Final[List[SpectrumMethod]] = [SpectrumMethod.FFT, SpectrumMethod.CQT]
EXPONENTS: Final[List[float]] = [1.0]
RUN_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1})
ITEM_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


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


class SilentReconstructor:
    """A reconstructor that converts nothing."""

    def __call__(self, path: Pathlike) -> Optional[Reconstruction]:
        return None


class RecordedReconstructors:
    """Builds silent reconstructors, noting the channels each is built over."""

    def __init__(self) -> None:
        self.built: List[FrozenSet[ChannelName]] = []

    def __call__(self, config: Config, channels: AbstractSet[ChannelName]) -> SilentReconstructor:
        self.built.append(frozenset(channels))
        return SilentReconstructor()


class TestEvaluateVariants:
    def test_an_item_naming_channels_is_converted_over_them_and_the_rest_over_the_run_s(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        recorded = RecordedReconstructors()
        monkeypatch.setattr("sampletones_tools.calibration.runner.ensure_library", lambda config: None)
        monkeypatch.setattr("sampletones_tools.calibration.runner.Reconstructor", recorded)
        items = [
            CorpusItem(name=name, category="tone", audio=np.zeros(1), truth=None, channels=channels)
            for name, channels in (("a", None), ("b", ITEM_CHANNELS), ("c", None), ("d", ITEM_CHANNELS))
        ]
        (variant,) = build_variants(Config(), [SpectrumMethod.FFT], EXPONENTS, [])

        evaluate_variants([variant], items, {item.name: tmp_path for item in items}, [], [], tmp_path, RUN_CHANNELS)

        assert recorded.built == [RUN_CHANNELS, ITEM_CHANNELS]
