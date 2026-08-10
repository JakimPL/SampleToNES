from pathlib import Path
from typing import List

import numpy as np
import pytest

from sampletones_application.services.render.constants import SCRATCH_SUFFIX
from sampletones_application.services.render.result import RenderResult, RenderStage
from sampletones_application.services.render.service import SongRenderService
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from tests.suite.base import BaseTestSuite
from tests.unit.sampletones_application.services.render.conftest import (
    LEVEL,
    TOTAL_SAMPLES,
    FakeSynthesizer,
    read_samples,
    wave_spec,
)


def _render(
    destination: Path,
    synthesizer: FakeSynthesizer,
    *,
    normalize: bool = False,
    total_samples: int = TOTAL_SAMPLES,
) -> List[RenderResult]:
    """Runs one render to completion, returning everything it reported."""
    service = SongRenderService()
    results: List[RenderResult] = []
    service.subscribe(results.append)
    service.start(
        synthesizer=synthesizer,
        destination=destination,
        spec=wave_spec(),
        normalize=normalize,
        total_samples=total_samples,
    )
    return results


def _progress(results: List[RenderResult], stage: RenderStage) -> List[ServiceProgress[RenderStage]]:
    return [result for result in results if isinstance(result, ServiceProgress) and result.current_item is stage]


class TestARenderReachesItsFile(BaseTestSuite):
    """A render that runs to the end leaves the whole song at the destination."""

    def test_the_success_names_the_destination(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        results = _render(destination, FakeSynthesizer())

        assert results[-1] == ServiceSuccess(value=destination)

    def test_the_file_holds_every_row(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer())

        assert len(read_samples(destination)) == TOTAL_SAMPLES

    def test_the_song_is_rendered_from_its_first_row(self, tmp_path: Path) -> None:
        """A render describes the document, so where a listener left the playhead does not reach it."""
        synthesizer = FakeSynthesizer()

        _render(tmp_path / "song.wav", synthesizer)

        assert synthesizer.positions[0] == (0, 0)
        assert synthesizer.resets == 1

    def test_the_first_report_states_the_total(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer())

        assert results[0] == ServiceStarted(total=TOTAL_SAMPLES)


class TestProgressIsReported(BaseTestSuite):
    """Every pass reports the samples it has covered, against the total the song holds."""

    def test_synthesis_progress_climbs_to_the_total(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer())
        reports = _progress(results, RenderStage.SYNTHESIS)

        assert [report.completed for report in reports] == sorted(report.completed for report in reports)
        assert reports[-1].completed == TOTAL_SAMPLES

    def test_every_report_is_measured_against_the_song(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer())
        reports = _progress(results, RenderStage.SYNTHESIS)

        assert all(report.total == TOTAL_SAMPLES for report in reports)

    def test_a_direct_render_reports_one_pass(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer())

        assert not _progress(results, RenderStage.ENCODING)

    def test_a_normalized_render_reports_both_passes(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer(), normalize=True)

        assert _progress(results, RenderStage.SYNTHESIS)
        assert _progress(results, RenderStage.ENCODING)

    def test_the_encoding_pass_climbs_to_the_total(self, tmp_path: Path) -> None:
        results = _render(tmp_path / "song.wav", FakeSynthesizer(), normalize=True)
        reports = _progress(results, RenderStage.ENCODING)

        assert reports[-1].completed == TOTAL_SAMPLES


class TestNormalizing(BaseTestSuite):
    """Normalising scales the whole render by what its loudest sample turned out to be."""

    def test_the_peak_reaches_full_scale(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer(), normalize=True)

        assert float(np.abs(read_samples(destination)).max()) == pytest.approx(1.0, abs=1e-4)

    def test_a_direct_render_keeps_the_level_it_was_given(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer())

        assert float(np.abs(read_samples(destination)).max()) == pytest.approx(LEVEL, abs=1e-4)

    def test_silence_is_written_as_it_stands(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer(level=0.0), normalize=True)

        assert not float(np.abs(read_samples(destination)).max())

    def test_the_spill_file_is_removed(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer(), normalize=True)

        assert not (tmp_path / f"song.wav{SCRATCH_SUFFIX}").exists()


class TestCancelling(BaseTestSuite):
    """A cancelled render reports itself cancelled and names no file."""

    def _cancelling_synthesizer(self, service: SongRenderService) -> FakeSynthesizer:
        return FakeSynthesizer(on_row=lambda rendered: service.cancel() if rendered == 4 else None)

    def test_a_cancelled_render_leaves_no_file(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"
        service = SongRenderService()
        service.start(
            synthesizer=self._cancelling_synthesizer(service),
            destination=destination,
            spec=wave_spec(),
            normalize=False,
            total_samples=TOTAL_SAMPLES,
        )

        assert not destination.exists()

    def test_a_cancelled_render_reports_itself_cancelled(self, tmp_path: Path) -> None:
        service = SongRenderService()
        results: List[RenderResult] = []
        service.subscribe(results.append)
        service.start(
            synthesizer=self._cancelling_synthesizer(service),
            destination=tmp_path / "song.wav",
            spec=wave_spec(),
            normalize=False,
            total_samples=TOTAL_SAMPLES,
        )

        assert results[-1] == ServiceCancelled()

    def test_a_cancelled_normalized_render_leaves_no_spill(self, tmp_path: Path) -> None:
        service = SongRenderService()
        service.start(
            synthesizer=self._cancelling_synthesizer(service),
            destination=tmp_path / "song.wav",
            spec=wave_spec(),
            normalize=True,
            total_samples=TOTAL_SAMPLES,
        )

        assert not list(tmp_path.iterdir())


class TestFailing(BaseTestSuite):
    """A render that raises reports the failure and takes its partial file with it."""

    def test_the_failure_is_reported(self, tmp_path: Path) -> None:
        error = RuntimeError("no sample")

        results = _render(tmp_path / "song.wav", FakeSynthesizer(error=error))
        reported = results[-1]

        assert isinstance(reported, ServiceError)
        assert reported.exception is error

    def test_the_partial_file_is_removed(self, tmp_path: Path) -> None:
        destination = tmp_path / "song.wav"

        _render(destination, FakeSynthesizer(error=RuntimeError("no sample")))

        assert not destination.exists()

    def test_a_failing_render_stops_running(self, tmp_path: Path) -> None:
        service = SongRenderService()
        service.start(
            synthesizer=FakeSynthesizer(error=RuntimeError("no sample")),
            destination=tmp_path / "song.wav",
            spec=wave_spec(),
            normalize=False,
            total_samples=TOTAL_SAMPLES,
        )

        assert not service.is_running()


class TestOneRenderAtATime(BaseTestSuite):
    """A render holds the service until it finishes, so a second request is declined."""

    def test_a_request_arriving_mid_render_is_declined(self, tmp_path: Path) -> None:
        service = SongRenderService()
        declined: List[bool] = []

        def request_again(rendered: int) -> None:
            if rendered:
                return

            declined.append(
                service.start(
                    synthesizer=FakeSynthesizer(),
                    destination=tmp_path / "second.wav",
                    spec=wave_spec(),
                    normalize=False,
                    total_samples=TOTAL_SAMPLES,
                )
            )

        service.start(
            synthesizer=FakeSynthesizer(on_row=request_again),
            destination=tmp_path / "song.wav",
            spec=wave_spec(),
            normalize=False,
            total_samples=TOTAL_SAMPLES,
        )

        assert declined == [False]
        assert not (tmp_path / "second.wav").exists()

    def test_the_service_is_free_once_a_render_finishes(self, tmp_path: Path) -> None:
        service = SongRenderService()
        service.start(
            synthesizer=FakeSynthesizer(),
            destination=tmp_path / "song.wav",
            spec=wave_spec(),
            normalize=False,
            total_samples=TOTAL_SAMPLES,
        )

        assert not service.is_running()
