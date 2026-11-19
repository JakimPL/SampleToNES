from pathlib import Path
from typing import AbstractSet, Final, FrozenSet, List, Optional

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.paths.extensions import EXT_FILE_FLAC, EXT_FILE_JSON
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.evaluation import evaluate_variants
from sampletones_tools.calibration.layout import RECORDINGS_DIRECTORY, RENDERS_DIRECTORY
from sampletones_tools.calibration.runner import CalibrationVariant, build_variants

from .conversions import StubReferee, WrittenReconstructor, item_named

ENSURE_LIBRARY: Final[str] = "sampletones_tools.calibration.evaluation.ensure_library"
RECONSTRUCTOR: Final[str] = "sampletones_tools.calibration.evaluation.Reconstructor"
RUN_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1})
ITEM_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())


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


@pytest.fixture(name="variant")
def variant_fixture(monkeypatch: pytest.MonkeyPatch) -> CalibrationVariant:
    monkeypatch.setattr(ENSURE_LIBRARY, lambda config: None)
    (variant,) = build_variants(Config(), [SpectrumMethod.FFT], [1.0], [])
    return variant


def _evaluated(
    variant: CalibrationVariant,
    items: List[CorpusItem],
    run_directory: Path,
    *,
    resume: bool,
) -> List[str]:
    rows = evaluate_variants(
        [variant],
        items,
        {item.name: run_directory / item.name for item in items},
        [StubReferee()],
        [],
        run_directory,
        RUN_CHANNELS,
        workers=1,
        resume=resume,
    )
    return [row.item for row in rows]


class TestEvaluateVariants:
    def test_an_item_naming_channels_is_converted_over_them_and_the_rest_over_the_run_s(
        self,
        variant: CalibrationVariant,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        recorded = RecordedReconstructors()
        monkeypatch.setattr(RECONSTRUCTOR, recorded)
        items = [
            CorpusItem(
                name=name,
                family=Family.SINES,
                category="tone",
                listed=True,
                audio=np.zeros(1),
                truth=None,
                channels=channels,
            )
            for name, channels in (("a", None), ("b", ITEM_CHANNELS), ("c", None), ("d", ITEM_CHANNELS))
        ]

        _evaluated(variant, items, tmp_path, resume=False)

        assert recorded.built == [RUN_CHANNELS, ITEM_CHANNELS]

    def test_a_listed_item_writes_its_audio_and_an_unlisted_one_its_record_alone(
        self,
        variant: CalibrationVariant,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels: WrittenReconstructor())

        _evaluated(
            variant, [item_named("shown", listed=True), item_named("measured", listed=False)], tmp_path, resume=False
        )

        renders = tmp_path / RENDERS_DIRECTORY / variant.label
        assert (renders / get_filename("shown", EXT_FILE_FLAC)).is_file()
        assert (tmp_path / RECORDINGS_DIRECTORY / get_filename("shown", EXT_FILE_FLAC)).is_file()
        assert (renders / get_filename("measured", EXT_FILE_JSON)).is_file()
        assert not (renders / get_filename("measured", EXT_FILE_FLAC)).exists()
        assert not (tmp_path / RECORDINGS_DIRECTORY / get_filename("measured", EXT_FILE_FLAC)).exists()


class TestResuming:
    def test_a_resumed_run_takes_the_recorded_rows_and_converts_only_the_rest(
        self,
        variant: CalibrationVariant,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        first = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels: first)
        whole = _evaluated(variant, [item_named("a", listed=False)], tmp_path, resume=False)
        second = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels: second)

        resumed = _evaluated(
            variant, [item_named("a", listed=False), item_named("b", listed=False)], tmp_path, resume=True
        )

        assert whole == ["a"]
        assert resumed == ["a", "b"]
        assert second.converted == [tmp_path / "b"]

    def test_a_fresh_run_converts_everything_again(
        self,
        variant: CalibrationVariant,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        reconstructor = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels: reconstructor)
        _evaluated(variant, [item_named("a", listed=False)], tmp_path, resume=False)

        _evaluated(variant, [item_named("a", listed=False)], tmp_path, resume=False)

        assert reconstructor.converted == [tmp_path / "a", tmp_path / "a"]
