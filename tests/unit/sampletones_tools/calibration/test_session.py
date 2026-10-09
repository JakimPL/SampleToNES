from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, FrozenSet, List

import pytest

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, SpectrumMethod
from sampletones_tools.calibration.board.layout import PAGE_FILE
from sampletones_tools.calibration.board.palette import DEFAULT_PALETTE
from sampletones_tools.calibration.board.session import BoardRequest
from sampletones_tools.calibration.corpus.item import CorpusItem
from sampletones_tools.calibration.layout import CSV_REPORT, MARKDOWN_REPORT
from sampletones_tools.calibration.referee.protocol import Referee
from sampletones_tools.calibration.runner import CalibrationRow, CalibrationVariant
from sampletones_tools.calibration.session import (
    BOARD_ROOT,
    OUTPUT_ROOT,
    CalibrationRequest,
    base_configuration,
    calibrate,
    default_output,
    default_page_output,
    floats_named,
    methods_named,
)
from sampletones_tools.runs import BOARD_STAMP, RUN_STAMP
from tests.unit.sampletones_tools.calibration.runs import write_run

EVALUATE = "sampletones_tools.calibration.session.evaluate_variants"
BUILD_BOARD = "sampletones_tools.calibration.session.build_board"


class TestMethodsNamed:
    def test_nothing_named_is_the_default(self) -> None:
        assert methods_named(None, (SpectrumMethod.LOG_SPACED_FFT,)) == [SpectrumMethod.LOG_SPACED_FFT]

    def test_names_are_read_in_order(self) -> None:
        assert methods_named("cqt, fft", ()) == [SpectrumMethod.CQT, SpectrumMethod.FFT]

    def test_an_unknown_method_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(ValueError, match="Unknown spectrum method 'dct'; the methods are"):
            methods_named("fft,dct", ())


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
        saved = defaults.model_copy(update={"general": defaults.general.model_copy(update={"max_workers": 3})})
        path = tmp_path / "config.json"
        saved.save(path)

        assert base_configuration(path).general.max_workers == 3


class TestCalibrate:
    def test_a_run_returns_its_report_beside_the_table_of_scores(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(EVALUATE, _evaluated([]))
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path / "run",
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1],
        )

        outcome = calibrate(request)

        assert outcome.report == tmp_path / "run" / MARKDOWN_REPORT
        assert outcome.report.is_file()
        assert (tmp_path / "run" / CSV_REPORT).is_file()

    def test_a_run_ends_with_the_page_its_renders_are_heard_on(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(EVALUATE, _evaluated([]))
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path / "run",
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1],
        )

        outcome = calibrate(request)

        assert outcome.page == tmp_path / "run" / PAGE_FILE
        assert outcome.page.is_file()

    def test_a_run_draws_its_page_in_the_palette_it_is_asked_for(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        drawn: List[str] = []
        monkeypatch.setattr(EVALUATE, _evaluated([]))
        monkeypatch.setattr(BUILD_BOARD, _built(drawn))
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path / "run",
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1],
            palette="light",
        )

        calibrate(request)

        assert drawn == ["light"]

    def test_a_run_asked_for_no_palette_draws_its_page_in_the_application_default(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        drawn: List[str] = []
        monkeypatch.setattr(EVALUATE, _evaluated([]))
        monkeypatch.setattr(BUILD_BOARD, _built(drawn))
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path / "run",
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1],
        )

        calibrate(request)

        assert drawn == [DEFAULT_PALETTE]

    def test_a_run_evaluates_with_the_channels_it_is_asked_for(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        asked: List[FrozenSet[ChannelName]] = []
        monkeypatch.setattr(EVALUATE, _evaluated(asked))
        request = CalibrationRequest(
            base=Config(),
            output=tmp_path / "run",
            methods=[SpectrumMethod.FFT],
            perceptual_exponents=[1.0],
            temporal_weights=[],
            channels=[ChannelName.PULSE1, ChannelName.NOISE],
        )

        calibrate(request)

        assert asked == [frozenset({ChannelName.PULSE1, ChannelName.NOISE})]


class TestCalibrationRequest:
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


def _evaluated(asked: List[FrozenSet[ChannelName]]) -> Callable[..., List[CalibrationRow]]:
    """An evaluation writing the renders a run writes, so the page the run ends with has clips."""

    def evaluated(
        variants: List[CalibrationVariant],
        items: List[CorpusItem],
        item_paths: Dict[str, Path],
        referees: List[Referee],
        run_directory: Path,
        channels: FrozenSet[ChannelName],
    ) -> List[CalibrationRow]:
        asked.append(channels)
        write_run(run_directory, [variant.label for variant in variants], 0.0)
        return []

    return evaluated


def _built(drawn: List[str]) -> Callable[[BoardRequest], Path]:
    def built(request: BoardRequest) -> Path:
        drawn.append(request.palette)
        return request.output / PAGE_FILE

    return built
