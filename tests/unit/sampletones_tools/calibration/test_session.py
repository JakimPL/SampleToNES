from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Final, FrozenSet, List, Tuple

import pytest
from pydantic import ValidationError

from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.board.layout import PAGE_FILE
from sampletones_tools.calibration.board.reading import read_run
from sampletones_tools.calibration.board.session import BoardRequest
from sampletones_tools.calibration.config.level import VariantLevel
from sampletones_tools.calibration.config.settings import SettingsConfig
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.fingerprint import FINGERPRINT_FILE, ResumeRefusedError
from sampletones_tools.calibration.layout import CSV_REPORT, MARKDOWN_REPORT, RECORDINGS_DIRECTORY, RENDERS_DIRECTORY
from sampletones_tools.calibration.referee.panel import RefereePanel
from sampletones_tools.calibration.rows import CalibrationRow
from sampletones_tools.calibration.session import (
    BOARD_ROOT,
    OUTPUT_ROOT,
    CalibrationRequest,
    base_configuration,
    calibrate,
    default_output,
    default_page_output,
)
from sampletones_tools.calibration.variants import CalibrationVariant
from sampletones_tools.runs import BOARD_STAMP, RUN_STAMP
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.unit.sampletones_tools.calibration.conversions import (
    UnavailableReconstructor,
    WrittenReconstructor,
    stub_panel,
)
from tests.unit.sampletones_tools.calibration.runs import write_renders, write_run

EVALUATE: Final[str] = "sampletones_tools.calibration.session.evaluate_variants"
BUILD_BOARD: Final[str] = "sampletones_tools.calibration.session.build_board"
BUILD_PANEL: Final[str] = "sampletones_tools.calibration.session.build_panel"
ENSURE_LIBRARY: Final[str] = "sampletones_tools.calibration.evaluation.ensure_library"
RECONSTRUCTOR: Final[str] = "sampletones_tools.calibration.evaluation.level_reconstructor"
LOAD_SETTINGS: Final[str] = "sampletones_tools.calibration.session.SettingsConfig.load"
CATEGORIES: Final[List[str]] = ["tone"]
OWN_FILE: Final[str] = "own.flac"
OWN_BYTES: Final[bytes] = b"a recording of the user's own"


class RecordedEvaluation:
    """An evaluation writing the renders a run writes, so the page the run ends with has clips.

    It notes what each evaluation is handed, and what the run directory holds when it starts.
    """

    def __init__(self) -> None:
        self.channels: List[FrozenSet[ChannelName]] = []
        self.categories: List[str] = []
        self.claimed: List[bool] = []
        self.corpus_written: List[bool] = []

    def __call__(
        self,
        variants: List[CalibrationVariant],
        items: List[CorpusItem],
        item_paths: Dict[str, Tuple[Path, ...]],
        panel: RefereePanel,
        run_directory: Path,
        channels: FrozenSet[ChannelName],
        *,
        workers: int,
        resume: bool,
    ) -> List[CalibrationRow]:
        self.channels.append(channels)
        self.categories.extend(item.category for item in items)
        self.claimed.append((run_directory / FINGERPRINT_FILE).is_file())
        self.corpus_written.append(all(path.is_file() for paths in item_paths.values() for path in paths))
        for variant in variants:
            write_renders(run_directory, [variant.label], 0.0, level=variant.level)

        return []


class RecordedBoard:
    """A page builder noting the palette each page is drawn in."""

    def __init__(self) -> None:
        self.palettes: List[str] = []

    def __call__(self, request: BoardRequest) -> Path:
        self.palettes.append(request.palette)
        return request.output / PAGE_FILE


@pytest.fixture(name="evaluation")
def evaluation_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedEvaluation:
    evaluation = RecordedEvaluation()
    monkeypatch.setattr(EVALUATE, evaluation)
    return evaluation


@pytest.fixture(name="board")
def board_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedBoard:
    board = RecordedBoard()
    monkeypatch.setattr(BUILD_BOARD, board)
    return board


@pytest.fixture(name="written")
def written_fixture(monkeypatch: pytest.MonkeyPatch) -> WrittenReconstructor:
    """Every conversion made by the written reconstructor and judged by the stub referee, every library ready."""
    reconstructor = WrittenReconstructor()
    monkeypatch.setattr(ENSURE_LIBRARY, lambda config: None)
    monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: reconstructor)
    monkeypatch.setattr(BUILD_PANEL, lambda sample_rate: stub_panel())
    return reconstructor


@pytest.fixture(name="asked")
def asked_fixture(tmp_path: Path) -> CalibrationRequest:
    return CalibrationRequest(
        base=Config(),
        output=tmp_path / "run",
        methods=[SpectrumMethod.FFT],
        perceptual_exponents=[1.0],
        temporal_weights=[],
        channels=[ChannelName.PULSE1],
        settings=[],
        levels=[VariantLevel.DEFAULT],
        categories=CATEGORIES,
        workers=1,
        resume=False,
        corpus=None,
    )


class TestDefaultOutput:
    def test_a_run_lands_in_a_timestamped_directory_under_the_documents(self) -> None:
        output = default_output()

        assert output.parent == OUTPUT_ROOT
        assert datetime.strptime(output.name, RUN_STAMP)

    def test_a_page_comparing_runs_lands_beside_them(self) -> None:
        output = default_page_output()

        assert output.parent == BOARD_ROOT
        assert datetime.strptime(output.name, BOARD_STAMP)


class TestBaseConfiguration:
    def test_without_a_file_the_run_measures_the_default_settings(self) -> None:
        assert base_configuration(None) == Config()

    def test_a_file_is_read_as_it_stands(self, tmp_path: Path) -> None:
        defaults = Config()
        saved = defaults.with_workers(3)
        path = tmp_path / "config.json"
        saved.save(path)

        assert base_configuration(path).general.max_workers == 3


class TestCalibrate:
    def test_a_run_returns_its_report_beside_the_table_of_scores(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        outcome = calibrate(asked)

        assert outcome.report == asked.output / MARKDOWN_REPORT
        assert outcome.report.is_file()
        assert (asked.output / CSV_REPORT).is_file()

    def test_a_run_ends_with_the_page_its_renders_are_heard_on(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        outcome = calibrate(asked)

        assert outcome.page == asked.output / PAGE_FILE
        assert outcome.page.is_file()

    def test_a_run_draws_its_page_in_the_palette_it_is_asked_for(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation, board: RecordedBoard
    ) -> None:
        calibrate(asked.model_copy(update={"palette": "light"}))

        assert board.palettes == ["light"]

    def test_a_run_asked_for_no_palette_draws_its_page_in_the_application_default(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation, board: RecordedBoard
    ) -> None:
        calibrate(asked)

        assert board.palettes == [DEFAULT_PALETTE_NAME]

    def test_a_run_evaluates_with_the_channels_it_is_asked_for(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        calibrate(asked.model_copy(update={"channels": [ChannelName.PULSE1, ChannelName.NOISE]}))

        assert evaluation.channels == [frozenset({ChannelName.PULSE1, ChannelName.NOISE})]

    def test_a_run_measures_the_sounds_of_the_categories_it_is_asked_for(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        calibrate(asked.model_copy(update={"categories": ["sequences-melody", "tone"]}))

        assert set(evaluation.categories) == {"sequences-melody", "tone"}

    def test_a_run_claims_its_directory_and_writes_its_corpus_before_converting(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        calibrate(asked)

        assert evaluation.claimed == [True]
        assert evaluation.corpus_written == [True]


class TestARunInAUsedFolder:
    """A fresh run claims its folder whole, so its page and a later resume read its own records alone.

    It clears the renders and recordings of the run that claimed the folder before, and refuses a
    folder whose renders or recordings no run claimed, leaving them as they stand.
    """

    def test_a_folder_an_earlier_run_claimed_is_cleared(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        write_run(asked.output, ["cqt-pe1"], 0.0)
        write_renders(asked.output, ["cqt-pe1-true"], 0.0, level=VariantLevel.TRUE)

        calibrate(asked)

        assert [path.name for path in (asked.output / RENDERS_DIRECTORY).iterdir()] == ["fft-pe1"]
        assert not (asked.output / RECORDINGS_DIRECTORY / VariantLevel.TRUE.value).exists()

    @pytest.mark.parametrize("held", [RENDERS_DIRECTORY, RECORDINGS_DIRECTORY], ids=lambda held: held)
    def test_a_folder_holding_files_no_run_claimed_is_refused_and_left_as_it_stands(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation, held: str
    ) -> None:
        own = asked.output / held / OWN_FILE
        own.parent.mkdir(parents=True)
        own.write_bytes(OWN_BYTES)

        with pytest.raises(ResumeRefusedError, match="holds files no calibration run claimed"):
            calibrate(asked)

        assert own.read_bytes() == OWN_BYTES
        assert [path.name for path in asked.output.iterdir()] == [held]
        assert not evaluation.channels

    def test_an_empty_folder_is_claimed(self, asked: CalibrationRequest, evaluation: RecordedEvaluation) -> None:
        asked.output.mkdir()

        calibrate(asked)

        assert (asked.output / FINGERPRINT_FILE).is_file()
        assert len(evaluation.channels) == 1

    def test_a_fresh_run_over_an_earlier_one_leaves_its_own_records_alone(
        self, asked: CalibrationRequest, written: WrittenReconstructor
    ) -> None:
        earlier = asked.model_copy(
            update={"methods": [SpectrumMethod.FFT, SpectrumMethod.CQT], "levels": [VariantLevel.TRUE]}
        )
        calibrate(earlier)
        assert (asked.output / RECORDINGS_DIRECTORY / VariantLevel.TRUE.value).is_dir()

        calibrate(asked.model_copy(update={"methods": [SpectrumMethod.CQT]}))

        assert [path.name for path in (asked.output / RENDERS_DIRECTORY).iterdir()] == ["cqt-pe1"]
        assert not (asked.output / RECORDINGS_DIRECTORY / VariantLevel.TRUE.value).exists()
        assert read_run(asked.output, "run").variants == ("cqt-pe1",)

    def test_a_resume_reads_none_of_an_earlier_run_s_records(
        self,
        asked: CalibrationRequest,
        written: WrittenReconstructor,
        board: RecordedBoard,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        calibrate(asked)
        measured = len(written.converted)
        other = asked.model_copy(update={"channels": [ChannelName.NOISE]})
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: UnavailableReconstructor())
        calibrate(other)
        monkeypatch.setattr(RECONSTRUCTOR, lambda config, channels, level: written)

        calibrate(other.model_copy(update={"resume": True}))

        assert len(written.converted) == 2 * measured


class TestResumingARun:
    def test_a_folder_holding_no_run_is_refused(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        with pytest.raises(ResumeRefusedError, match="holds no run"):
            calibrate(asked.model_copy(update={"resume": True}))

        assert not evaluation.channels

    def test_a_run_resumes_the_run_it_left(self, asked: CalibrationRequest, evaluation: RecordedEvaluation) -> None:
        calibrate(asked)
        fingerprint = (asked.output / FINGERPRINT_FILE).read_text(encoding="utf-8")

        assert calibrate(asked.model_copy(update={"resume": True})).report.is_file()
        assert (asked.output / FINGERPRINT_FILE).read_text(encoding="utf-8") == fingerprint

    def test_a_run_measured_otherwise_is_refused(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        calibrate(asked)

        with pytest.raises(ResumeRefusedError, match="measured other variants"):
            calibrate(asked.model_copy(update={"resume": True, "methods": [SpectrumMethod.CQT]}))

        assert len(evaluation.channels) == 1

    def test_a_run_resumes_over_the_same_channels_named_in_another_order(
        self, asked: CalibrationRequest, evaluation: RecordedEvaluation
    ) -> None:
        calibrate(asked.model_copy(update={"channels": [ChannelName.PULSE1, ChannelName.NOISE]}))

        resumed = asked.model_copy(update={"channels": [ChannelName.NOISE, ChannelName.PULSE1], "resume": True})

        assert calibrate(resumed).report.is_file()
        assert len(evaluation.channels) == 2


class TestCalibrationRequest:
    @pytest.mark.parametrize(
        "field", ["methods", "perceptual_exponents", "channels", "levels", "categories"], ids=lambda field: field
    )
    def test_an_empty_part_of_the_sweep_is_refused(self, asked: CalibrationRequest, field: str) -> None:
        with pytest.raises(ValueError):
            CalibrationRequest.model_validate({**dict(asked), field: []})

    def test_a_run_of_no_worker_is_refused(self, asked: CalibrationRequest) -> None:
        with pytest.raises(ValueError):
            CalibrationRequest.model_validate({**dict(asked), "workers": 0})

    def test_a_set_naming_a_setting_the_configuration_lacks_is_refused(
        self, asked: CalibrationRequest, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        catalog = SettingsConfig(settings={"typo": {"generation": {"decoder": {"selektor": "greedy"}}}})
        monkeypatch.setattr(LOAD_SETTINGS, lambda: catalog)

        with pytest.raises(ValidationError):
            CalibrationRequest.model_validate({**dict(asked), "settings": ["typo"]})


class TestSharedLabels(BaseTestSuite):
    """A request whose sweep names two variants alike is refused as it is read, naming the label."""

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
    def test_a_sweep_naming_two_variants_alike_is_refused_naming_them(
        self, test_case: TestCase, asked: CalibrationRequest
    ) -> None:
        swept = {"methods": test_case.methods, "perceptual_exponents": test_case.exponents}

        with pytest.raises(ValueError, match=f"named {test_case.shared};"):
            CalibrationRequest.model_validate({**dict(asked), **swept})
