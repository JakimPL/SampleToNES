from pathlib import Path
from typing import AbstractSet, Final, FrozenSet, List, Optional, Tuple

import numpy as np
import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstructor.observer import SILENT_OBSERVER, ReconstructionObserver
from sampletones_shared.paths.extensions import EXT_FILE_FLAC, EXT_FILE_JSON
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.corpus.by_channel import by_channel
from sampletones_tools.calibration.corpus.chords import build_chords
from sampletones_tools.calibration.corpus.families import Family
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.evaluation import evaluate_variants
from sampletones_tools.calibration.layout import RECORDINGS_DIRECTORY, RENDERS_DIRECTORY
from sampletones_tools.calibration.referee.protocol import SCORE_READING
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants

from .conversions import WrittenReconstructor, item_named, stub_panel
from .corpus.test_by_channel import CHORDS

ENSURE_LIBRARY: Final[str] = "sampletones_tools.calibration.evaluation.ensure_library"
RECONSTRUCTOR: Final[str] = "sampletones_tools.calibration.evaluation.level_reconstructor"
RUN_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1})
ITEM_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset(ChannelName.items())

Converted = List[Tuple[str, str]]


class SilentReconstructor:
    """A reconstructor that converts nothing, noting each path it is handed."""

    def __init__(self) -> None:
        self.converted: List[Pathlike] = []

    def __call__(
        self, path: Pathlike, *, observe: ReconstructionObserver = SILENT_OBSERVER
    ) -> Optional[Reconstruction]:
        self.converted.append(path)
        return None


class RecordedReconstructors:
    """Builds silent reconstructors, noting the channels each is built over."""

    def __init__(self) -> None:
        self.built: List[FrozenSet[ChannelName]] = []

    def __call__(self, config: Config, channels: AbstractSet[ChannelName], level: WorkingLevel) -> SilentReconstructor:
        self.built.append(frozenset(channels))
        return SilentReconstructor()


@pytest.fixture(name="libraries")
def libraries_fixture(monkeypatch: pytest.MonkeyPatch) -> List[Config]:
    ensured: List[Config] = []
    monkeypatch.setattr(ENSURE_LIBRARY, ensured.append)
    return ensured


@pytest.fixture(name="variants")
def variants_fixture(libraries: List[Config]) -> List[CalibrationVariant]:
    return build_variants(
        Config(),
        [SpectrumMethod.FFT, SpectrumMethod.CQT],
        [1.0],
        [],
        settings={},
        levels=[WorkingLevel.DEFAULT],
    )


@pytest.fixture(name="variant")
def variant_fixture(variants: List[CalibrationVariant]) -> CalibrationVariant:
    return variants[0]


@pytest.fixture(name="written")
def written_fixture(monkeypatch: pytest.MonkeyPatch) -> WrittenReconstructor:
    reconstructor = WrittenReconstructor()
    monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: reconstructor)
    return reconstructor


def _evaluated(
    variants: List[CalibrationVariant],
    items: List[CorpusItem],
    run_directory: Path,
    *,
    resume: bool,
) -> Converted:
    """The (variant, sound) of every score row the run returns, in its order."""
    rows = evaluate_variants(
        variants,
        items,
        {item.name: (run_directory / item.name,) for item in items},
        stub_panel(),
        run_directory,
        RUN_CHANNELS,
        workers=1,
        resume=resume,
    )
    return [(row.variant, row.item) for row in rows if row.component == SCORE_READING]


def _items(*names: str) -> List[CorpusItem]:
    return [item_named(name, listed=False) for name in names]


class TestEvaluateVariants:
    def test_the_rows_come_variant_by_variant_each_in_corpus_order(
        self, variants: List[CalibrationVariant], written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        converted = _evaluated(variants, _items("a", "b"), tmp_path, resume=False)

        labels = [variant.label for variant in variants]
        assert converted == [(labels[0], "a"), (labels[0], "b"), (labels[1], "a"), (labels[1], "b")]

    def test_every_variant_s_library_is_made_ready_before_any_conversion(
        self,
        variants: List[CalibrationVariant],
        libraries: List[Config],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ready_at_first_build: List[int] = []

        def reconstructor(
            config: Config, channels: AbstractSet[ChannelName], level: WorkingLevel
        ) -> SilentReconstructor:
            ready_at_first_build.append(len(libraries))
            return SilentReconstructor()

        monkeypatch.setattr(RECONSTRUCTOR, reconstructor)

        _evaluated(variants, _items("a"), tmp_path, resume=False)

        assert libraries == [variant.config for variant in variants]
        assert ready_at_first_build[0] == len(variants)

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
                stems=None,
            )
            for name, channels in (("a", None), ("b", ITEM_CHANNELS), ("c", None), ("d", ITEM_CHANNELS))
        ]

        _evaluated([variant], items, tmp_path, resume=False)

        assert recorded.built == [RUN_CHANNELS, ITEM_CHANNELS]

    def test_a_listed_item_writes_its_audio_and_an_unlisted_one_its_record_alone(
        self, variant: CalibrationVariant, written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        _evaluated(
            [variant], [item_named("shown", listed=True), item_named("measured", listed=False)], tmp_path, resume=False
        )

        renders = tmp_path / RENDERS_DIRECTORY / variant.label
        assert (renders / get_filename("shown", EXT_FILE_FLAC)).is_file()
        assert (tmp_path / RECORDINGS_DIRECTORY / get_filename("shown", EXT_FILE_FLAC)).is_file()
        assert (renders / get_filename("measured", EXT_FILE_JSON)).is_file()
        assert not (renders / get_filename("measured", EXT_FILE_FLAC)).exists()
        assert not (tmp_path / RECORDINGS_DIRECTORY / get_filename("measured", EXT_FILE_FLAC)).exists()

    def test_an_empty_corpus_converts_nothing(
        self, variants: List[CalibrationVariant], written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        assert not _evaluated(variants, [], tmp_path, resume=False)
        assert not written.converted


class TestResuming:
    """A resumed run takes each recorded conversion's rows from its record and converts the rest, in the run's order."""

    def test_a_resumed_run_takes_the_recorded_rows_and_converts_only_the_rest(
        self, variant: CalibrationVariant, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        first = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: first)
        whole = _evaluated([variant], _items("a"), tmp_path, resume=False)
        second = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: second)

        resumed = _evaluated([variant], _items("a", "b"), tmp_path, resume=True)

        assert whole == [(variant.label, "a")]
        assert resumed == [(variant.label, "a"), (variant.label, "b")]
        assert second.converted == [tmp_path / "b"]

    def test_a_record_between_pending_conversions_keeps_its_place(
        self, variants: List[CalibrationVariant], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        later = variants[1]
        first = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: first)
        _evaluated([later], _items("b"), tmp_path, resume=False)
        second = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: second)

        resumed = _evaluated(variants, _items("a", "b", "c"), tmp_path, resume=True)

        labels = [variant.label for variant in variants]
        assert resumed == [(label, item) for label in labels for item in ("a", "b", "c")]
        assert len(second.converted) == 5

    def test_a_conversion_that_left_no_record_is_converted_again(
        self, variant: CalibrationVariant, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        unavailable = SilentReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: unavailable)
        _evaluated([variant], _items("a"), tmp_path, resume=False)
        second = WrittenReconstructor()
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: second)

        resumed = _evaluated([variant], _items("a"), tmp_path, resume=True)

        assert resumed == [(variant.label, "a")]
        assert second.converted == [tmp_path / "a"]

    def test_a_fully_recorded_run_converts_nothing(
        self, variant: CalibrationVariant, written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        _evaluated([variant], _items("a", "b"), tmp_path, resume=False)
        written.converted.clear()

        resumed = _evaluated([variant], _items("a", "b"), tmp_path, resume=True)

        assert resumed == [(variant.label, "a"), (variant.label, "b")]
        assert not written.converted

    def test_a_fresh_run_converts_everything_again(
        self, variant: CalibrationVariant, written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        _evaluated([variant], _items("a"), tmp_path, resume=False)

        _evaluated([variant], _items("a"), tmp_path, resume=False)

        assert written.converted == [tmp_path / "a", tmp_path / "a"]


class TestStems:
    def test_a_sound_held_as_stems_is_converted_under_its_setup_from_every_stem(
        self, variant: CalibrationVariant, written: WrittenReconstructor, tmp_path: Path
    ) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)
        split = by_channel(chord, Config())
        paths = (tmp_path / "chord-stem0.wav", tmp_path / "chord-stem1.wav")

        evaluate_variants(
            [variant], [split], {split.name: paths}, stub_panel(), tmp_path, RUN_CHANNELS, workers=1, resume=False
        )

        assert written.converted == list(paths)
