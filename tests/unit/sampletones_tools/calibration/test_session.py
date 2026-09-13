from pathlib import Path

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_shared.paths.user import USER_PATH_DOCUMENTS
from sampletones_tools.calibration.session import (
    CalibrationRequest,
    default_output,
    floats_named,
    methods_named,
)


class TestMethodsNamed:
    def test_nothing_named_is_fft_and_cqt(self) -> None:
        assert methods_named(None) == [SpectrumMethod.FFT, SpectrumMethod.CQT]

    def test_names_are_read_in_order(self) -> None:
        assert methods_named("cqt, fft") == [SpectrumMethod.CQT, SpectrumMethod.FFT]

    def test_an_unknown_method_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="Unknown spectrum method 'dct'; the methods are"):
            methods_named("fft,dct")


class TestFloatsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert floats_named(None, (1.0,)) == [1.0]
        assert floats_named(None, ()) == []

    def test_values_are_read_in_order(self) -> None:
        assert floats_named("0.5, 1", ()) == [0.5, 1.0]

    def test_a_value_that_is_no_number_is_refused(self) -> None:
        with pytest.raises(ValueError, match="Not a number: 'high'"):
            floats_named("0.5,high", ())


class TestDefaultOutput:
    def test_a_run_lands_in_a_timestamped_directory_under_the_documents(self) -> None:
        output = default_output()

        assert output.parent == USER_PATH_DOCUMENTS / "calibration"
        assert output.name.startswith("run-")


class TestCalibrationRequest:
    def test_the_base_is_pinned_to_the_channels(self, tmp_path: Path) -> None:
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path,
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1],
        )

        assert request.pinned_base().generation.channels == [ChannelName.PULSE1]

    def test_an_empty_sweep_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError):
            CalibrationRequest(
                base=Config(),
                output=tmp_path,
                methods=[],
                perceptual_exponents=[1.0],
                temporal_weights=[],
                channels=[ChannelName.PULSE1],
            )
