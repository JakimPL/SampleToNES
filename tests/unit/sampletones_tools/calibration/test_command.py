from pathlib import Path
from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.config.suite import SuiteConfig
from sampletones_tools.calibration.layout import MARKDOWN_REPORT
from sampletones_tools.calibration.session import OUTPUT_ROOT, CalibrationRequest

CALIBRATE = "sampletones_tools.calibration.session.calibrate"


class RecordedCalibration:
    def __init__(self) -> None:
        self.requests: List[CalibrationRequest] = []

    def __call__(self, request: CalibrationRequest) -> Path:
        self.requests.append(request)
        return request.output / MARKDOWN_REPORT


@pytest.fixture(name="calibration")
def calibration_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedCalibration:
    recorded = RecordedCalibration()
    monkeypatch.setattr(CALIBRATE, recorded)
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


class TestPrintedLink:
    def test_a_run_prints_the_link_to_its_report(
        self,
        calibration: RecordedCalibration,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        run = tmp_path / "run"

        assert dispatch(COMMANDS, ["calibration", "-o", str(run)]) == 0

        assert capsys.readouterr().out.splitlines() == [f"Report: {(run / MARKDOWN_REPORT).resolve().as_uri()}"]
