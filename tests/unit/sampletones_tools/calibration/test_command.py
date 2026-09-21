from pathlib import Path
from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.board.layout import PAGE_FILE
from sampletones_tools.calibration.board.palette import DEFAULT_PALETTE
from sampletones_tools.calibration.board.session import BoardRequest
from sampletones_tools.calibration.config.suite import SuiteConfig
from sampletones_tools.calibration.layout import MARKDOWN_REPORT
from sampletones_tools.calibration.session import (
    BOARD_ROOT,
    OUTPUT_ROOT,
    CalibrationOutcome,
    CalibrationRequest,
)
from tests.unit.sampletones_tools.calibration.runs import write_run

CALIBRATE = "sampletones_tools.calibration.session.calibrate"
BUILD_BOARD = "sampletones_tools.calibration.board.session.build_board"
OPEN_PAGE = "sampletones_tools.calibration.board.browser.open_page"


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
        assert request.output.parent == OUTPUT_ROOT

    def test_a_configuration_file_is_measured_in_place_of_the_defaults(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
    ) -> None:
        defaults = Config()
        saved = defaults.model_copy(update={"general": defaults.general.model_copy(update={"max_workers": 2})})
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

    def test_the_page_is_drawn_in_the_palette_named(self, calibration: RecordedCalibration) -> None:
        assert dispatch(COMMANDS, ["calibration", "--palette", "light"]) == 0

        assert calibration.requests[0].palette == "light"

    def test_without_a_palette_the_page_takes_the_application_default(
        self,
        calibration: RecordedCalibration,
    ) -> None:
        assert dispatch(COMMANDS, ["calibration"]) == 0

        assert calibration.requests[0].palette == DEFAULT_PALETTE


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

    def test_a_page_measures_nothing_so_it_takes_no_measuring_option(
        self,
        board: RecordedBoard,
        tmp_path: Path,
    ) -> None:
        run = write_run(tmp_path / "before", ["cqt-pe1"], 0.0)

        with pytest.raises(SystemExit, match="measures nothing"):
            dispatch(COMMANDS, ["calibration", "--board", str(run), "--methods", "fft"])

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
