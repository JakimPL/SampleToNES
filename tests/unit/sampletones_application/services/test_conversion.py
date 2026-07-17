from pathlib import Path
from time import sleep
from typing import Any, List
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.services.conversion import ConversionService
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceIntermediate,
    ServiceProgress,
    ServiceStarted,
    ServiceSuccess,
)
from sampletones_core.parallelization import TaskProgress, TaskStatus


@pytest.fixture
def mock_converter_class():
    with patch("sampletones_application.services.conversion.ReconstructionConverter") as cls:
        instance = MagicMock()
        instance.is_running.return_value = False
        instance.status = TaskStatus.COMPLETED
        instance.total_tasks = 5

        captured: SerializedData = {}
        instance.set_callbacks.side_effect = lambda **kwargs: captured.update(kwargs)

        cls.return_value = instance
        yield cls, instance, captured


@pytest.fixture
def service(mock_converter_class):
    cls, instance, callbacks = mock_converter_class
    conversion_service = ConversionService()
    results: List[Any] = []
    conversion_service.subscribe(results.append)

    input_path = MagicMock(spec=Path)
    input_path.is_file.return_value = True
    conversion_service.start(MagicMock(), input_path)

    return conversion_service, instance, callbacks, results


class TestConversionServiceStart:
    def test_start_creates_and_starts_converter(self, mock_converter_class) -> None:
        cls, instance, _ = mock_converter_class
        conversion_service = ConversionService()
        conversion_service.start(MagicMock(), MagicMock())

        cls.assert_called_once()
        instance.start.assert_called_once()

    def test_start_wires_five_lifecycle_callbacks(self, mock_converter_class) -> None:
        _, _, callbacks = mock_converter_class
        conversion_service = ConversionService()
        conversion_service.start(MagicMock(), MagicMock())

        assert set(callbacks.keys()) == {"on_start", "on_progress", "on_completed", "on_error", "on_cancelled"}

    def test_start_while_running_does_not_create_second_converter(self, mock_converter_class) -> None:
        cls, instance, _ = mock_converter_class
        instance.is_running.return_value = True
        instance.status = TaskStatus.RUNNING

        conversion_service = ConversionService()
        conversion_service.start(MagicMock(), MagicMock())
        conversion_service.start(MagicMock(), MagicMock())

        assert cls.call_count == 1


class TestConversionServiceEmissions:
    def test_on_start_emits_service_started_with_total(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceStarted)
        assert result.total == 5

    def test_on_progress_running_emits_service_progress(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=2, current_item="/some/file.wav")
        callbacks["on_progress"](TaskStatus.RUNNING, progress)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceProgress)
        assert result.completed == 2
        assert result.total == 5
        assert result.current_item == Path("/some/file.wav")

    def test_on_progress_cancelling_emits_service_progress(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=3)
        callbacks["on_progress"](TaskStatus.CANCELLING, progress)

        assert len(results) == 1
        assert isinstance(results[0], ServiceProgress)

    def test_on_progress_pending_does_not_emit(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=0)
        callbacks["on_progress"](TaskStatus.PENDING, progress)

        assert results == []

    def test_on_progress_completed_does_not_emit(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=5)
        callbacks["on_progress"](TaskStatus.COMPLETED, progress)

        assert results == []

    def test_on_progress_current_item_none_when_absent(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=1)
        callbacks["on_progress"](TaskStatus.RUNNING, progress)

        assert results[0].current_item is None

    def test_on_completed_emits_service_success(self, service) -> None:
        _, _, callbacks, results = service
        output_path = Path("/output/result.nes")
        callbacks["on_completed"](output_path)

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
        assert results[0].value == output_path

    def test_on_error_emits_service_error(self, service) -> None:
        _, _, callbacks, results = service
        exception = RuntimeError("converter failed")
        callbacks["on_error"](exception)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceError)
        assert result.exception is exception

    def test_on_cancelled_emits_service_cancelled(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_cancelled"]()

        assert len(results) == 1
        assert isinstance(results[0], ServiceCancelled)

    def test_forward_library_progress_emits_service_intermediate(self, service) -> None:
        conversion_service, _, _, results = service
        task_progress = TaskProgress(total=10, completed=4)
        conversion_service.forward_library_progress(TaskStatus.RUNNING, task_progress)

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceIntermediate)
        assert result.data is task_progress


class TestConversionServiceETA:
    def test_eta_estimator_none_before_on_start_fires(self, service) -> None:
        conversion_service, _, _, _ = service
        assert conversion_service._eta_estimator is None

    def test_eta_estimator_created_after_on_start(self, service) -> None:
        conversion_service, _, callbacks, _ = service
        callbacks["on_start"]()
        assert conversion_service._eta_estimator is not None

    def test_eta_seconds_none_with_single_sample(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        progress = TaskProgress(total=5, completed=1)
        callbacks["on_progress"](TaskStatus.RUNNING, progress)

        assert results[0].eta_seconds is None

    def test_eta_seconds_populated_after_two_samples(self, service) -> None:
        _, _, callbacks, results = service
        callbacks["on_start"]()
        results.clear()

        callbacks["on_progress"](
            TaskStatus.RUNNING,
            TaskProgress(
                total=10,
                completed=1,
            ),
        )
        sleep(0.02)
        callbacks["on_progress"](
            TaskStatus.RUNNING,
            TaskProgress(
                total=10,
                completed=2,
            ),
        )

        assert results[-1].eta_seconds is not None
        assert results[-1].eta_seconds > 0

    def test_eta_estimator_reset_on_cleanup(self, service) -> None:
        conversion_service, _, callbacks, _ = service
        callbacks["on_start"]()
        assert conversion_service._eta_estimator is not None

        conversion_service.cleanup()

        assert conversion_service._eta_estimator is None


class TestConversionServiceLifecycle:
    def test_cleanup_resets_converter(self, service) -> None:
        conversion_service, _, _, _ = service
        conversion_service.cleanup()
        assert conversion_service._converter is None

    def test_cleanup_disposes_running_converter(self, service) -> None:
        conversion_service, converter, _, _ = service
        converter.is_running.return_value = True
        conversion_service.cleanup()
        converter.cleanup.assert_called_once()
        assert conversion_service._converter is None

    def test_shutdown_tears_down_converter_synchronously(self, service) -> None:
        conversion_service, converter, _, _ = service
        conversion_service.shutdown()
        converter.shutdown.assert_called_once()
        assert conversion_service._converter is None

    def test_is_running_true_when_converter_running(self, service) -> None:
        conversion_service, converter, _, _ = service
        converter.is_running.return_value = True
        assert conversion_service.is_running()

    def test_is_running_true_when_converter_pending(self, service) -> None:
        conversion_service, converter, _, _ = service
        converter.is_running.return_value = False
        converter.status = TaskStatus.PENDING
        assert conversion_service.is_running()

    def test_is_running_false_when_converter_none(self) -> None:
        conversion_service = ConversionService()
        assert not conversion_service.is_running()

    def test_cancel_delegates_to_converter(self, service) -> None:
        conversion_service, converter, _, _ = service
        converter.is_running.return_value = True
        conversion_service.cancel()
        converter.cancel.assert_called_once()

    def test_cancel_when_not_running_does_not_call_converter_cancel(self, service) -> None:
        conversion_service, converter, _, _ = service
        converter.is_running.return_value = False
        conversion_service.cancel()
        converter.cancel.assert_not_called()
