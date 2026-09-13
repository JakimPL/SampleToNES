from pathlib import Path
from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.configs import Config
from sampletones_core.constants.enums import DEFAULT_CHANNELS, ChannelName, SpectrumMethod
from sampletones_tools.calibration.session import OUTPUT_ROOT, CalibrationRequest

CALIBRATE = "sampletones_tools.calibration.session.calibrate"
LOADER = "sampletones_core.headless.config.load_config"


class RecordedCalibration:
    def __init__(self) -> None:
        self.requests: List[CalibrationRequest] = []

    def __call__(self, request: CalibrationRequest) -> Path:
        self.requests.append(request)
        return request.output


@pytest.fixture(name="calibration")
def calibration_fixture(monkeypatch: pytest.MonkeyPatch) -> RecordedCalibration:
    recorded = RecordedCalibration()
    monkeypatch.setattr(CALIBRATE, recorded)
    monkeypatch.setattr(LOADER, lambda path: Config())
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

    def test_without_options_the_run_sweeps_both_methods_into_the_documents(
        self,
        calibration: RecordedCalibration,
    ) -> None:
        assert dispatch(COMMANDS, ["calibration"]) == 0
        request = calibration.requests[0]
        assert request.methods == [SpectrumMethod.FFT, SpectrumMethod.CQT]
        assert request.perceptual_exponents == [1.0]
        assert request.temporal_weights == []
        assert request.channels == list(DEFAULT_CHANNELS)
        assert request.output.parent == OUTPUT_ROOT

    def test_an_unknown_method_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Unknown spectrum method"):
            dispatch(COMMANDS, ["calibration", "--methods", "dct"])

        assert calibration.requests == []

    def test_a_value_that_is_no_number_is_refused(self, calibration: RecordedCalibration) -> None:
        with pytest.raises(SystemExit, match="Not a number"):
            dispatch(COMMANDS, ["calibration", "--perceptual-exponents", "high"])

        assert calibration.requests == []
