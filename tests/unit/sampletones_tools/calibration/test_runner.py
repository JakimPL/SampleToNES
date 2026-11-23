from dataclasses import dataclass, replace
from pathlib import Path
from typing import Final, FrozenSet, List, Optional, Sequence, Tuple, cast

import numpy as np
import pytest

from sampletones_core.audio.io import read_wave
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_core.reconstructions import Reconstruction, Reconstructor
from sampletones_core.reconstructions.reconstructor.decoder.base import Alternatives
from sampletones_core.reconstructions.reconstructor.observer import SILENT_OBSERVER, ReconstructionObserver
from sampletones_core.reconstructions.reconstructor.stems.configs.config import StemsConfig
from sampletones_shared.paths.extensions import EXT_FILE_FLAC
from sampletones_shared.types.path import Pathlike
from sampletones_shared.utils.system.paths import get_filename
from sampletones_tools.calibration import renders
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.config.referee import RefereeConfig
from sampletones_tools.calibration.corpus.by_channel import by_channel
from sampletones_tools.calibration.corpus.chords import build_chords
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.corpus.truth import Truth
from sampletones_tools.calibration.layout import RECORDINGS_DIRECTORY
from sampletones_tools.calibration.referee.panel import RefereePanel
from sampletones_tools.calibration.referee.protocol import Judgment
from sampletones_tools.calibration.renders import RenderRecord, read_record, recording_path, variant_directory
from sampletones_tools.calibration.rows import recorded_rows
from sampletones_tools.calibration.runner import Conversion, evaluate_conversion
from sampletones_tools.calibration.trace import SearchTrace, TraceRecorder
from sampletones_tools.calibration.variants import CalibrationVariant, build_variants
from sampletones_tools.corpus.written import NO_RECORDINGS, WRITTEN_SCALE, written_reconstruction
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

from .conversions import UnavailableReconstructor, WrittenReconstructor, item_named, stub_panel
from .corpus.test_by_channel import CHORDS

RUN_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.PULSE1})
ITEM_CHANNELS: Final[FrozenSet[ChannelName]] = frozenset({ChannelName.TRIANGLE, ChannelName.NOISE})
HALF_LEVEL: Final[float] = 0.5
SCORE: Final[float] = 1.0
WRITE_RECORD: Final[str] = "sampletones_tools.calibration.renders.write_record"
QUANTIZATION_TOLERANCE: Final[float] = 1.0 / 2**15


@pytest.fixture(name="variant")
def variant_fixture() -> CalibrationVariant:
    (variant,) = build_variants(Config(), [SpectrumMethod.FFT], [1.0], [], settings={}, levels=[WorkingLevel.DEFAULT])
    return variant


def _conversion(variant: CalibrationVariant, item: CorpusItem, run_directory: Path) -> Conversion:
    return Conversion(
        variant=variant,
        item=item,
        position=0,
        paths=(run_directory / f"{item.name}-0.wav", run_directory / f"{item.name}-1.wav"),
        run_channels=RUN_CHANNELS,
        run_directory=run_directory,
    )


class StemsReconstructor(WrittenReconstructor):
    """The written reconstructor, noting the stems setup it converts under."""

    def __init__(self) -> None:
        super().__init__()
        self.setups: List[StemsConfig] = []

    def reconstruct(
        self,
        paths: Sequence[Pathlike],
        stems_config: StemsConfig,
        *,
        observe: ReconstructionObserver = SILENT_OBSERVER,
    ) -> Optional[Reconstruction]:
        self.setups.append(stems_config)
        return super().reconstruct(paths, stems_config, observe=observe)


class HalfLevelReconstructor(WrittenReconstructor):
    """The written reconstructor, matching at half the level its recording plays at."""

    def __init__(self) -> None:
        super().__init__()
        self.reconstruction = written_reconstruction(
            self.reconstruction.instructions,
            coefficient=HALF_LEVEL,
            scale=WRITTEN_SCALE,
            audio_filepath=NO_RECORDINGS,
        )


class QuietFileReconstructor(WrittenReconstructor):
    """The written reconstructor, reading its file at half the level, as a level reading files unnormalized may."""

    def load_audio(self, paths: Sequence[Pathlike]) -> np.ndarray:
        return HALF_LEVEL * super().load_audio(paths)


class TracingReconstructor(WrittenReconstructor):
    """The written reconstructor, telling its observer it assigned and decoded."""

    def __call__(
        self, path: Pathlike, *, observe: ReconstructionObserver = SILENT_OBSERVER
    ) -> Optional[Reconstruction]:
        observe.assigned(Alternatives(lattices={}, pools={}))
        observe.decoded({})
        return super().__call__(path, observe=observe)


@dataclass(frozen=True)
class NamedJudge:
    """A referee of any kind, answering a fixed judgment or none, and noting each estimate it judges."""

    name: str
    answers: bool
    estimates: List[np.ndarray]

    def judgment(self) -> Optional[Judgment]:
        return Judgment(score=SCORE, components={}) if self.answers else None


class AudioJudge(NamedJudge):
    def judge(self, reference: np.ndarray, estimate: np.ndarray) -> Judgment:
        self.estimates.append(estimate)
        return Judgment(score=SCORE, components={})


class TruthJudge(NamedJudge):
    def judge(self, truth: Truth, reconstruction: Reconstruction) -> Optional[Judgment]:
        return self.judgment()


class TraceJudge(NamedJudge):
    def judge(self, truth: Truth, trace: SearchTrace, reconstruction: Reconstruction) -> Optional[Judgment]:
        return self.judgment()


class ConversionJudge(NamedJudge):
    def judge(self, reconstruction: Reconstruction) -> Optional[Judgment]:
        return self.judgment()


def _panel(*, answering: bool) -> RefereePanel:
    return RefereePanel(
        audio=(AudioJudge("audio", True, []),),
        truth=(TruthJudge("truth", answering, []),),
        trace=(TraceJudge("trace", answering, []),),
        conversion=(ConversionJudge("conversion", answering, []),),
        config=RefereeConfig.load(),
    )


class TestConversion:
    def test_a_sound_naming_no_channels_converts_over_the_run_s(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        conversion = _conversion(variant, item_named("a", listed=False), tmp_path)

        assert conversion.channels == RUN_CHANNELS

    def test_a_sound_naming_channels_converts_over_its_own(self, variant: CalibrationVariant, tmp_path: Path) -> None:
        item = replace(item_named("a", listed=False), channels=ITEM_CHANNELS)

        assert _conversion(variant, item, tmp_path).channels == ITEM_CHANNELS

    def test_a_sound_of_one_recording_converts_its_first_file_alone(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        conversion = _conversion(variant, item_named("a", listed=False), tmp_path)
        reconstructor = StemsReconstructor()

        conversion.reconstruct(cast(Reconstructor, reconstructor), TraceRecorder())

        assert conversion.stems is None
        assert reconstructor.converted == [conversion.paths[0]]
        assert not reconstructor.setups

    def test_a_sound_held_as_stems_converts_every_file_under_its_setup(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        (chord,) = build_chords(Config(), corpus=CHORDS)
        split = by_channel(chord, Config())
        assert split.stems is not None
        conversion = _conversion(variant, split, tmp_path)
        reconstructor = StemsReconstructor()

        conversion.reconstruct(cast(Reconstructor, reconstructor), TraceRecorder())

        assert conversion.stems == split.stems.config
        assert reconstructor.converted == list(conversion.paths)
        assert reconstructor.setups == [split.stems.config]


class TestEvaluateConversion:
    def test_the_rows_returned_are_the_ones_the_record_keeps(self, variant: CalibrationVariant, tmp_path: Path) -> None:
        item = item_named("a", listed=False)

        rows = evaluate_conversion(
            _conversion(variant, item, tmp_path), cast(Reconstructor, WrittenReconstructor()), stub_panel()
        )

        record = read_record(tmp_path, variant.label, item.name)
        assert record is not None
        assert [row.referee for row in rows] == ["stub", "stub"]
        assert rows == recorded_rows(record)

    def test_an_unavailable_reconstruction_leaves_no_row_and_no_record(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        item = item_named("a", listed=True)

        rows = evaluate_conversion(
            _conversion(variant, item, tmp_path), cast(Reconstructor, UnavailableReconstructor()), stub_panel()
        )

        assert not rows
        assert read_record(tmp_path, variant.label, item.name) is None
        assert not tmp_path.joinpath(RECORDINGS_DIRECTORY).exists()

    def test_silence_is_judged_by_every_audio_referee_against_the_recording(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        panel = _panel(answering=True)
        item = item_named("a", listed=False)

        evaluate_conversion(_conversion(variant, item, tmp_path), cast(Reconstructor, WrittenReconstructor()), panel)

        record = read_record(tmp_path, variant.label, item.name)
        assert record is not None
        assert record.silence == {"audio": SCORE}
        render, silence = cast(AudioJudge, panel.audio[0]).estimates
        assert np.any(render)
        assert not np.any(silence)
        assert silence.shape == render.shape

    def test_a_listed_sound_s_record_is_written_after_its_audio(
        self, variant: CalibrationVariant, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        item = item_named("a", listed=True)
        render = variant_directory(tmp_path, variant.label) / get_filename(item.name, EXT_FILE_FLAC)
        recording = tmp_path / RECORDINGS_DIRECTORY / get_filename(item.name, EXT_FILE_FLAC)
        standing: List[Tuple[bool, bool]] = []
        write_record = renders.write_record

        def noting(run_directory: Path, record: RenderRecord) -> None:
            standing.append((render.is_file(), recording.is_file()))
            write_record(run_directory, record)

        monkeypatch.setattr(WRITE_RECORD, noting)

        evaluate_conversion(
            _conversion(variant, item, tmp_path), cast(Reconstructor, WrittenReconstructor()), stub_panel()
        )

        assert standing == [(True, True)]

    def test_a_listed_sound_is_written_back_at_its_recording_s_level(
        self, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        item = item_named("a", listed=True)
        reconstructor = HalfLevelReconstructor()

        evaluate_conversion(_conversion(variant, item, tmp_path), cast(Reconstructor, reconstructor), stub_panel())

        recording, _ = read_wave(tmp_path / RECORDINGS_DIRECTORY / get_filename(item.name, EXT_FILE_FLAC))
        render, _ = read_wave(variant_directory(tmp_path, variant.label) / get_filename(item.name, EXT_FILE_FLAC))
        heard = reconstructor.load_audio([])
        assert np.allclose(recording, heard[: recording.shape[0]], atol=QUANTIZATION_TOLERANCE)
        assert np.allclose(render, heard[: render.shape[0]] * HALF_LEVEL, atol=QUANTIZATION_TOLERANCE)

    def test_a_record_keeps_the_level_its_render_was_matched_at(self, tmp_path: Path) -> None:
        (true,) = build_variants(Config(), [SpectrumMethod.FFT], [1.0], [], settings={}, levels=[WorkingLevel.TRUE])
        item = item_named("a", listed=False)

        evaluate_conversion(
            _conversion(true, item, tmp_path), cast(Reconstructor, WrittenReconstructor()), stub_panel()
        )

        record = read_record(tmp_path, true.label, item.name)
        assert record is not None
        assert record.level == WorkingLevel.TRUE

    def test_each_level_keeps_its_own_recording_of_a_listed_sound(self, tmp_path: Path) -> None:
        default, true = build_variants(
            Config(), [SpectrumMethod.FFT], [1.0], [], settings={}, levels=[WorkingLevel.DEFAULT, WorkingLevel.TRUE]
        )
        item = item_named("a", listed=True)
        normalized, quiet = WrittenReconstructor(), QuietFileReconstructor()

        evaluate_conversion(_conversion(default, item, tmp_path), cast(Reconstructor, normalized), stub_panel())
        evaluate_conversion(_conversion(true, item, tmp_path), cast(Reconstructor, quiet), stub_panel())

        at_default, _ = read_wave(recording_path(tmp_path, WorkingLevel.DEFAULT, item.name))
        at_true, _ = read_wave(recording_path(tmp_path, WorkingLevel.TRUE, item.name))
        assert np.allclose(at_default, normalized.load_audio([])[: at_default.shape[0]], atol=QUANTIZATION_TOLERANCE)
        assert np.allclose(at_true, quiet.load_audio([])[: at_true.shape[0]], atol=QUANTIZATION_TOLERANCE)


class TestJudgments(BaseTestSuite):
    """The referees judge in a fixed order, the audio ones leading, so the first heads the report and the page."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        truth: bool
        traced: bool
        answering: bool
        referees: List[str]

    test_cases = (
        TestCase(truth=False, traced=False, answering=True, referees=["audio", "conversion"], label="no_truth"),
        TestCase(truth=False, traced=True, answering=True, referees=["audio", "conversion"], label="trace_no_truth"),
        TestCase(
            truth=True, traced=False, answering=True, referees=["audio", "truth", "conversion"], label="truth_no_trace"
        ),
        TestCase(
            truth=True,
            traced=True,
            answering=True,
            referees=["audio", "truth", "trace", "conversion"],
            label="truth_and_trace",
        ),
        TestCase(truth=True, traced=True, answering=False, referees=["audio"], label="referees_with_no_reading"),
    )

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda case: case.label)
    def test_each_kind_judges_where_its_inputs_are_known(
        self, test_case: TestCase, variant: CalibrationVariant, tmp_path: Path
    ) -> None:
        truth = Truth(instructions={}, pitches={}) if test_case.truth else None
        item = replace(item_named("a", listed=False), truth=truth)
        reconstructor = TracingReconstructor() if test_case.traced else WrittenReconstructor()

        evaluate_conversion(
            _conversion(variant, item, tmp_path),
            cast(Reconstructor, reconstructor),
            _panel(answering=test_case.answering),
        )

        record = read_record(tmp_path, variant.label, item.name)
        assert record is not None
        assert list(record.judgments) == test_case.referees
