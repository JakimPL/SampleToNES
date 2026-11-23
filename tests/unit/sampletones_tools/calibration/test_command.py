import socket
from pathlib import Path
from typing import Final, Iterator, List

import pytest
import yaml

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_application.utils.palette.catalog import DEFAULT_PALETTE_NAME
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.board.layout import PAGE_FILE
from sampletones_tools.calibration.board.session import BoardRequest
from sampletones_tools.calibration.config.level import WorkingLevel
from sampletones_tools.calibration.config.samples import SampleReference, SamplesConfig
from sampletones_tools.calibration.config.settings import SettingsConfig
from sampletones_tools.calibration.config.suite import SuiteConfig
from sampletones_tools.calibration.corpus.reference import reference_categories
from sampletones_tools.calibration.fingerprint import ResumeRefusedError
from sampletones_tools.calibration.layout import MARKDOWN_REPORT
from sampletones_tools.calibration.samples import SAMPLES_DIRECTORY
from sampletones_tools.calibration.session import (
    BOARD_ROOT,
    OUTPUT_ROOT,
    CalibrationOutcome,
    CalibrationRequest,
)
from tests.unit.sampletones_tools.calibration.midifiles import nesmdb_archive
from tests.unit.sampletones_tools.calibration.runs import write_run

CALIBRATE = "sampletones_tools.calibration.session.calibrate"
MEASURING_OPTIONS: Final[List[List[str]]] = [
    ["--config", "config.json"],
    ["--methods", "fft"],
    ["--perceptual-exponents", "1"],
    ["--temporal-weights", "0.5"],
    ["--channels", "pulse1"],
    ["--settings", "greedy"],
    ["--levels", "true"],
    ["--categories", "tone"],
    ["--skip", "notes"],
    ["--workers", "2"],
    ["--resume"],
    ["--corpus", "manifest.yaml"],
]
BUILD_BOARD = "sampletones_tools.calibration.board.session.build_board"
OPEN_PAGE = "sampletones_tools.calibration.board.browser.open_page"
LOAD_SETTINGS = "sampletones_tools.calibration.config.settings.SettingsConfig.load"
LOAD_SAMPLES = "sampletones_tools.calibration.config.samples.SamplesConfig.load"
SAMPLES_FOLDER = "sampletones_tools.calibration.samples.SAMPLES_DIRECTORY"
DOWNLOAD_TIMEOUT = "sampletones_tools.calibration.samples.TIMEOUT_SECONDS"
STALL_SECONDS: Final[float] = 0.05
LOOPBACK: Final[str] = "127.0.0.1"


class RecordedCalibration:
    def __init__(self) -> None:
        self.requests: List[CalibrationRequest] = []

    def __call__(self, request: CalibrationRequest) -> CalibrationOutcome:
        self.requests.append(request)
        return CalibrationOutcome(
            report=request.output / MARKDOWN_REPORT,
            page=request.output / PAGE_FILE,
        )


class RecordedBoard:
    def __init__(self) -> None:
        self.requests: List[BoardRequest] = []

    def __call__(self, request: BoardRequest) -> Path:
        self.requests.append(request)
        return request.output / PAGE_FILE


@pytest.fixture(name="manifest")
def manifest_fixture(tmp_path: Path) -> Path:
    member = "nesmdb_midi/train/piece.mid"
    archive = nesmdb_archive(tmp_path, member)
    path = tmp_path / "manifest.yaml"
    item = {
        "kind": "nesmdb",
        "name": "piece",
        "archive": archive.name,
        "member": member,
        "start_frame": 0,
        "frames": 30,
        "split": "review",
    }
    path.write_text(yaml.safe_dump({"items": [item]}), encoding="utf-8")
    return path


@pytest.fixture(name="stalling")
def stalling_fixture() -> Iterator[str]:
    """The address of a publisher that takes every connection and answers none of them."""
    with socket.create_server((LOOPBACK, 0)) as server:
        host, port = server.getsockname()
        yield f"http://{host}:{port}/sample.wav"


@pytest.fixture(name="calibration")
def calibration_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedCalibration:
    recorded = RecordedCalibration()
    monkeypatch.setattr(CALIBRATE, recorded)
    monkeypatch.setattr(OPEN_PAGE, lambda page: True)
    return recorded


@pytest.fixture(name="board")
def board_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedBoard:
    recorded = RecordedBoard()
    monkeypatch.setattr(BUILD_BOARD, recorded)
    monkeypatch.setattr(OPEN_PAGE, lambda page: True)
    return recorded


class TestCalibration:
    def test_the_sweep_is_read_from_the_options(self, calibration: RecordedCalibration, tmp_path: Path) -> None:
        status = dispatch(
            COMMANDS,
            [
                "calibration",
                "--methods",
                "fft",
                "--perceptual-exponents",
                "0.5,1",
                "--temporal-weights",
                "0.25",
                "--channels",
                "pulse1",
                "--categories",
                "sequences-mixed,tone",
                "-o",
                str(tmp_path / "run"),
            ],
        )

        assert status == 0
        request = calibration.requests[0]
        assert request.methods == [SpectrumMethod.FFT]
        assert request.perceptual_exponents == [0.5, 1.0]
        assert request.temporal_weights == [0.25]
        assert request.channels == [ChannelName.PULSE1]
        assert request.categories == ["sequences-mixed", "tone"]
        assert request.output == tmp_path / "run"

    def test_without_options_the_run_measures_the_default_settings_under_the_suite(
        self,
        calibration: RecordedCalibration,
    ) -> None:
        suite = SuiteConfig.load()

        assert dispatch(COMMANDS, ["calibration"]) == 0

        request = calibration.requests[0]
        assert request.base == Config()
        assert request.methods == list(suite.methods)
        assert request.perceptual_exponents == list(suite.perceptual_exponents)
        assert request.temporal_weights == list(suite.temporal_weights)
        assert request.channels == list(suite.channels)
        assert request.settings == list(suite.settings)
        assert request.levels == list(suite.levels)
        assert request.categories == reference_categories(None)
        assert request.output.parent == OUTPUT_ROOT

    def test_a_configuration_file_is_measured_in_place_of_the_defaults(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
    ) -> None:
        defaults = Config()
        saved = defaults.with_workers(2)
        path = tmp_path / "config.json"
        saved.save(path)

        assert dispatch(COMMANDS, ["calibration", "--config", str(path)]) == 0

        assert calibration.requests[0].base.general.max_workers == 2

    def test_an_unknown_method_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Unknown spectrum method"):
            dispatch(COMMANDS, ["calibration", "--methods", "dct"])

        assert calibration.requests == []

    def test_a_value_that_is_no_number_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Not a number"):
            dispatch(COMMANDS, ["calibration", "--perceptual-exponents", "high"])

        assert calibration.requests == []

    def test_a_skipped_family_is_left_out_of_the_run(self, calibration: RecordedCalibration) -> None:
        assert dispatch(COMMANDS, ["calibration", "--skip", "sequences"]) == 0

        assert "sequences-mixed" not in calibration.requests[0].categories
        assert "tone" in calibration.requests[0].categories

    def test_the_workers_and_the_resume_are_read_from_the_options(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
    ) -> None:
        assert dispatch(COMMANDS, ["calibration", "--workers", "3", "--resume", "-o", str(tmp_path)]) == 0

        assert (calibration.requests[0].workers, calibration.requests[0].resume) == (3, True)

    def test_the_settings_and_the_levels_are_read_from_the_options(self, calibration: RecordedCalibration) -> None:
        assert dispatch(COMMANDS, ["calibration", "--settings", "greedy", "--levels", "default,true"]) == 0

        assert calibration.requests[0].settings == ["greedy"]
        assert calibration.requests[0].levels == [WorkingLevel.DEFAULT, WorkingLevel.TRUE]

    def test_an_unknown_set_of_settings_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Unknown set of settings"):
            dispatch(COMMANDS, ["calibration", "--settings", "gredy"])

        assert calibration.requests == []

    @pytest.mark.parametrize(
        "sweep",
        [["--methods", "cqt,cqt"], ["--methods", "fft", "--perceptual-exponents", "0.5,0.5000001"]],
        ids=["method", "exponent"],
    )
    def test_a_sweep_naming_two_variants_alike_exits_before_the_run_starts(
        self, calibration: RecordedCalibration, sweep: List[str]
    ) -> None:
        with pytest.raises(SystemExit, match="Several variants of the sweep are named"):
            dispatch(COMMANDS, ["calibration", *sweep])

        assert calibration.requests == []

    def test_a_set_naming_a_setting_the_configuration_lacks_exits_before_the_run_starts(
        self, calibration: RecordedCalibration, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        catalog = SettingsConfig(settings={"typo": {"generation": {"decoder": {"selektor": "greedy"}}}})
        monkeypatch.setattr(LOAD_SETTINGS, lambda: catalog)

        with pytest.raises(SystemExit, match="selektor"):
            dispatch(COMMANDS, ["calibration", "--settings", "typo"])

        assert calibration.requests == []

    def test_a_run_refused_its_resume_exits_naming_why(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        def refused(request: CalibrationRequest) -> CalibrationOutcome:
            raise ResumeRefusedError("measured other sounds")

        monkeypatch.setattr(CALIBRATE, refused)

        with pytest.raises(SystemExit, match="measured other sounds"):
            dispatch(COMMANDS, ["calibration", "--resume", "-o", str(tmp_path)])

    def test_without_workers_the_run_takes_the_configuration_s_own(self, calibration: RecordedCalibration) -> None:
        assert dispatch(COMMANDS, ["calibration"]) == 0

        assert calibration.requests[0].workers == Config().general.max_workers
        assert not calibration.requests[0].resume

    def test_a_manifest_s_sounds_join_the_categories_measured(
        self,
        calibration: RecordedCalibration,
        manifest: Path,
    ) -> None:
        assert dispatch(COMMANDS, ["calibration", "--corpus", str(manifest)]) == 0

        assert calibration.requests[0].corpus == manifest
        assert "nesmdb-review" in calibration.requests[0].categories

    def test_a_missing_manifest_is_refused(self, calibration: RecordedCalibration, tmp_path: Path) -> None:
        with pytest.raises(SystemExit):
            dispatch(COMMANDS, ["calibration", "--corpus", str(tmp_path / "absent.yaml")])

        assert calibration.requests == []

    def test_an_unknown_category_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Unknown category"):
            dispatch(COMMANDS, ["calibration", "--categories", "chord"])

        assert calibration.requests == []

    def test_the_page_is_drawn_in_the_palette_named(self, calibration: RecordedCalibration) -> None:
        assert dispatch(COMMANDS, ["calibration", "--palette", "light"]) == 0

        assert calibration.requests[0].palette == "light"

    def test_without_a_palette_the_page_takes_the_application_default(
        self,
        calibration: RecordedCalibration,
    ) -> None:
        assert dispatch(COMMANDS, ["calibration"]) == 0

        assert calibration.requests[0].palette == DEFAULT_PALETTE_NAME


class TestBoard:
    def test_the_runs_named_are_compared_on_one_page(
        self,
        board: RecordedBoard,
        tmp_path: Path,
    ) -> None:
        runs = [write_run(tmp_path / name, ["cqt-pe1"], 0.0) for name in ("before", "after")]
        output = tmp_path / "comparison"

        status = dispatch(COMMANDS, ["calibration", "--board", *[str(run) for run in runs], "-o", str(output)])

        assert status == 0
        assert board.requests[0].runs == runs
        assert board.requests[0].output == output

    def test_without_an_output_the_page_lands_beside_the_runs(
        self,
        board: RecordedBoard,
        tmp_path: Path,
    ) -> None:
        run = write_run(tmp_path / "before", ["cqt-pe1"], 0.0)

        assert dispatch(COMMANDS, ["calibration", "--board", str(run)]) == 0

        assert board.requests[0].output.parent == BOARD_ROOT

    @pytest.mark.parametrize("option", MEASURING_OPTIONS, ids=lambda option: option[0])
    def test_a_page_measures_nothing_so_it_takes_no_measuring_option(
        self,
        board: RecordedBoard,
        tmp_path: Path,
        option: List[str],
    ) -> None:
        run = write_run(tmp_path / "before", ["cqt-pe1"], 0.0)
        named = ", ".join(given[0] for given in MEASURING_OPTIONS)

        with pytest.raises(SystemExit, match=f"measures nothing; it takes none of {named}."):
            dispatch(COMMANDS, ["calibration", "--board", str(run), *option])

        assert board.requests == []

    def test_a_run_without_renders_is_reported(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(OPEN_PAGE, lambda page: True)
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(SystemExit, match="holds no calibration renders"):
            dispatch(COMMANDS, ["calibration", "--board", str(empty), "-o", str(tmp_path / "page")])


class TestPrintedLinks:
    def test_a_run_prints_the_links_to_its_report_and_its_page(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        run = tmp_path / "run"

        assert dispatch(COMMANDS, ["calibration", "-o", str(run)]) == 0

        assert capsys.readouterr().out.splitlines() == [
            f"Report: {(run / MARKDOWN_REPORT).resolve().as_uri()}",
            f"Page: {(run / PAGE_FILE).resolve().as_uri()}",
        ]

    def test_the_page_is_opened_unless_it_is_left_closed(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        opened: List[Path] = []
        monkeypatch.setattr(OPEN_PAGE, lambda page: bool(opened.append(page)) or True)

        assert dispatch(COMMANDS, ["calibration", "-o", str(tmp_path / "shown")]) == 0
        assert dispatch(COMMANDS, ["calibration", "-o", str(tmp_path / "quiet"), "--no-open"]) == 0

        assert opened == [tmp_path / "shown" / PAGE_FILE]


class TestFetchingSamples:
    def test_the_samples_are_fetched_into_the_calibration_folder_and_nothing_is_measured(
        self,
        calibration: RecordedCalibration,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        fetched: List[Path] = []
        monkeypatch.setattr(
            "sampletones_tools.calibration.samples.fetch_samples",
            lambda config, directory: fetched.append(directory) or [],
        )

        assert dispatch(COMMANDS, ["calibration", "--fetch-samples"]) == 0

        assert fetched == [SAMPLES_DIRECTORY]
        assert calibration.requests == []

    def test_fetching_the_samples_measures_nothing_whatever_else_is_named(
        self,
        calibration: RecordedCalibration,
        board: RecordedBoard,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        monkeypatch.setattr("sampletones_tools.calibration.samples.fetch_samples", lambda config, directory: [])

        assert dispatch(COMMANDS, ["calibration", "--fetch-samples", "--methods", "fft"]) == 0
        assert dispatch(COMMANDS, ["calibration", "--fetch-samples", "--board", str(tmp_path)]) == 0

        assert calibration.requests == []
        assert board.requests == []

    def test_a_download_that_stalls_after_connecting_ends_with_a_note(
        self,
        stalling: str,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        reference = SampleReference(
            name="stalled",
            url=stalling,
            file_name="stalled.wav",
            sha256="0" * 64,
            start_seconds=0.0,
            end_seconds=1.0,
            license="CC0 1.0",
            attribution="nobody",
        )
        monkeypatch.setattr(
            LOAD_SAMPLES, lambda: SamplesConfig(user_agent="test", pause_seconds=0.0, samples=[reference])
        )
        monkeypatch.setattr(SAMPLES_FOLDER, tmp_path)
        monkeypatch.setattr(DOWNLOAD_TIMEOUT, STALL_SECONDS)

        with pytest.raises(SystemExit, match="The samples could not be fetched"):
            dispatch(COMMANDS, ["calibration", "--fetch-samples"])

        assert list(tmp_path.iterdir()) == []
