import math
import warnings
from pathlib import Path
from typing import Final, List, cast

import pytest
from pydantic import ValidationError

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SelectorName, SpectrumMethod
from sampletones_core.reconstructions import Reconstructor
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.config.settings import Overrides
from sampletones_tools.calibration.renders import RenderRecord, read_record
from sampletones_tools.calibration.runner import (
    LOG_GAP,
    CalibrationVariant,
    Conversion,
    build_variants,
    evaluate_conversion,
    recorded_rows,
)

from .conversions import WrittenReconstructor, item_named, stub_panel

METHODS: Final[List[SpectrumMethod]] = [SpectrumMethod.FFT, SpectrumMethod.CQT]
EXPONENTS: Final[List[float]] = [1.0]
DEFAULT_LEVEL: Final[List[WorkingLevel]] = [WorkingLevel.DEFAULT]
GREEDY: Final[Overrides] = {"generation": {"decoder": {"selector": "greedy"}}}


def _variants(
    methods: List[SpectrumMethod],
    exponents: List[float],
    temporal_weights: List[float],
) -> List[CalibrationVariant]:
    return build_variants(Config(), methods, exponents, temporal_weights, settings={}, levels=DEFAULT_LEVEL)


class TestBuildVariants:
    def test_sweeps_every_combination(self) -> None:
        variants = _variants(METHODS, [1.0, 0.5], [0.25])
        assert [variant.label for variant in variants] == [
            "fft-pe1-tw0.25",
            "fft-pe0.5-tw0.25",
            "cqt-pe1-tw0.25",
            "cqt-pe0.5-tw0.25",
        ]

    @pytest.mark.parametrize("method", METHODS, ids=lambda method: method.value)
    def test_variant_holds_the_spectrum_method_member(self, method: SpectrumMethod) -> None:
        (variant,) = _variants([method], EXPONENTS, [])
        assert variant.config.library.spectrum_method is method

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
            settings={},
            levels=[WorkingLevel.DEFAULT, WorkingLevel.TRUE],
        )

        assert (default.label, true.label) == ("cqt-pe1", "cqt-pe1-true")
        assert (default.level, true.level) == (WorkingLevel.DEFAULT, WorkingLevel.TRUE)
        assert default.config.general.normalize == Config().general.normalize
        assert true.config.general.normalize is False


class TestEvaluateConversion:
    def test_the_rows_returned_are_the_ones_the_record_keeps(self, tmp_path: Path) -> None:
        (variant,) = _variants([SpectrumMethod.FFT], EXPONENTS, [])
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
        assert [row.referee for row in rows] == ["stub", "stub"]
        assert rows == recorded_rows(record)


def _record(score: float, silence: float) -> RenderRecord:
    return RenderRecord(
        variant="cqt-pe1",
        item="a",
        position=0,
        category="notes-pulse",
        timelines={},
        judgments={"auditory": {"score": score}},
        silence={"auditory": silence},
    )


class TestRecordedRows:
    def test_an_audio_score_also_reads_as_its_log_gap_to_silence(self) -> None:
        rows = recorded_rows(_record(score=2.0, silence=8.0))

        gaps = [row.score for row in rows if row.component == LOG_GAP]
        assert gaps == [pytest.approx(math.log(2.0 / 8.0))]

    @pytest.mark.parametrize("score, silence", [(0.0, 8.0), (2.0, 0.0)], ids=["exact_render", "silent_recording"])
    def test_a_score_or_silence_of_zero_reads_no_log_gap(self, score: float, silence: float) -> None:
        rows = recorded_rows(_record(score=score, silence=silence))

        assert [row.component for row in rows] == ["score"]
