from typing import Any, List
from unittest.mock import MagicMock

from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.services.retune import RetunedSample, SampleRetuneService


def _reconstruction(retuned: Any = None) -> MagicMock:
    reconstruction = MagicMock()
    reconstruction.with_nes_frequency.return_value = retuned if retuned is not None else MagicMock()
    return reconstruction


class TestSampleRetuneServiceRun:
    def test_emits_one_success_per_target(self) -> None:
        service = SampleRetuneService()
        results: List[Any] = []
        service.subscribe(results.append)
        first, second = _reconstruction(), _reconstruction()

        service._run([("a", first), ("b", second)], 60)

        assert [type(result) for result in results] == [ServiceSuccess, ServiceSuccess]
        assert [result.value.sample_id for result in results] == ["a", "b"]
        assert results[0].value.reconstruction is first.with_nes_frequency.return_value

    def test_retunes_each_target_to_the_requested_rate(self) -> None:
        service = SampleRetuneService()
        service.subscribe(lambda _result: None)
        first, second = _reconstruction(), _reconstruction()

        service._run([("a", first), ("b", second)], 120)

        first.with_nes_frequency.assert_called_once_with(120)
        second.with_nes_frequency.assert_called_once_with(120)

    def test_emits_service_error_when_a_retune_raises(self) -> None:
        service = SampleRetuneService()
        results: List[Any] = []
        service.subscribe(results.append)
        failing = MagicMock()
        failing.with_nes_frequency.side_effect = RuntimeError("resynthesis failed")

        service._run([("a", failing)], 60)

        assert len(results) == 1
        assert isinstance(results[0], ServiceError)

    def test_result_carries_the_sample_id_and_retuned_reconstruction(self) -> None:
        service = SampleRetuneService()
        results: List[Any] = []
        service.subscribe(results.append)
        retuned = MagicMock()

        service._run([("lead", _reconstruction(retuned))], 60)

        assert results[0].value == RetunedSample(sample_id="lead", reconstruction=retuned)


class TestSampleRetuneServiceStart:
    def test_start_runs_the_batch(self) -> None:
        service = SampleRetuneService()
        results: List[Any] = []
        service.subscribe(results.append)

        accepted = service.start([("a", _reconstruction())], 60)

        assert accepted is True
        assert len(results) == 1

    def test_is_running_delegates_to_the_executor(self) -> None:
        service = SampleRetuneService()
        service._executor = MagicMock()

        service._executor.is_running = True
        assert service.is_running() is True

        service._executor.is_running = False
        assert service.is_running() is False
