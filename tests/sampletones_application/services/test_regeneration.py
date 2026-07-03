import threading
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.services.regeneration import RegenerationService
from sampletones_application.services.result import ServiceCancelled, ServiceError, ServiceSuccess
from sampletones_application.utils.thread import SingleThreadExecutor
from sampletones_core.constants.enums import FeatureKey, GeneratorName

_real_executor_execute = SingleThreadExecutor.execute


@pytest.fixture
def synthesis_mocks():
    mock_instruction = MagicMock()
    mock_exporter = MagicMock()
    mock_generator_class = MagicMock()
    mock_generator = MagicMock(return_value=np.zeros(100))

    mock_generator_class.return_value = mock_generator
    mock_exporter.get_generator_type.return_value = mock_generator_class
    mock_exporter.from_features.return_value = [mock_instruction]

    generator_name = GeneratorName.PULSE1

    with patch(
        "sampletones_application.services.regeneration.GENERATOR_NAME_TO_EXPORTER_MAP",
        {generator_name: mock_exporter},
    ):
        yield SimpleNamespace(
            exporter=mock_exporter,
            generator_class=mock_generator_class,
            generator=mock_generator,
            instruction=mock_instruction,
            generator_name=generator_name,
        )


@pytest.fixture
def reconstruction():
    reconstruction = MagicMock()
    reconstruction.config = MagicMock()
    return reconstruction


class TestRegenerationServiceStart:
    def test_start_when_not_cancelled_returns_true(self, synthesis_mocks, reconstruction) -> None:
        service = RegenerationService()
        result = service.start(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            1,
        )
        assert result is True

    def test_start_when_cancelled_returns_false(self) -> None:
        service = RegenerationService()
        service.cancel()

        result = service.start(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock())

        assert result is False

    def test_start_when_cancelled_does_not_emit(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service.cancel()

        service.start(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock())

        assert results == []

    def test_start_when_executor_busy_returns_false(self) -> None:
        service = RegenerationService()
        with patch.object(service._executor, "execute", return_value=False):
            result = service.start(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock())

        assert result is False

    def test_cancel_sets_cancelled_flag(self) -> None:
        service = RegenerationService()
        assert not service._cancelled

        service.cancel()

        assert service._cancelled


class TestRegenerationServiceRun:
    def test_run_when_cancelled_emits_service_cancelled(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service._cancelled = True

        service._run(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock())

        assert len(results) == 1
        assert isinstance(results[0], ServiceCancelled)

    def test_run_success_emits_service_success(self, synthesis_mocks, reconstruction) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            1,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
        outcome = results[0].value
        assert outcome.reconstruction is reconstruction.model_copy.return_value
        assert outcome.reconstruction is not reconstruction
        assert outcome.generator_name is synthesis_mocks.generator_name
        assert outcome.feature_key is FeatureKey.VOLUME

    def test_run_updates_feature_before_synthesis(self, synthesis_mocks, reconstruction) -> None:
        service = RegenerationService()
        features: Dict[Any, Any] = {}
        feature_key = FeatureKey.VOLUME
        new_value = 42

        service._run(
            reconstruction,
            synthesis_mocks.generator_name,
            features,
            feature_key,
            new_value,
        )

        assert features[feature_key] == new_value

    def test_run_updates_reconstruction_copy(self, synthesis_mocks, reconstruction) -> None:
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            1,
        )

        updated = reconstruction.model_copy.return_value
        updated.update_generator_data.assert_called_once()
        reconstruction.update_generator_data.assert_not_called()
        call_args = updated.update_generator_data.call_args
        assert call_args.args[0] == synthesis_mocks.generator_name

    def test_run_calls_generator_for_each_instruction(self, synthesis_mocks, reconstruction) -> None:
        extra_instruction = MagicMock()
        synthesis_mocks.exporter.from_features.return_value = [synthesis_mocks.instruction, extra_instruction]
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            1,
        )

        assert synthesis_mocks.generator.call_count == 2

    def test_run_exception_emits_service_error(self, reconstruction) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        exception = RuntimeError("synthesis failed")
        mock_exporter = MagicMock()
        mock_exporter.get_generator_type.side_effect = exception

        with patch(
            "sampletones_application.services.regeneration.GENERATOR_NAME_TO_EXPORTER_MAP",
            {GeneratorName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                GeneratorName.PULSE1,
                {},
                FeatureKey.VOLUME,
                1,
            )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceError)
        assert result.exception is exception

    def test_run_exception_does_not_update_reconstruction(self, reconstruction) -> None:
        service = RegenerationService()
        mock_exporter = MagicMock()
        mock_exporter.get_generator_type.side_effect = RuntimeError("fail")

        with patch(
            "sampletones_application.services.regeneration.GENERATOR_NAME_TO_EXPORTER_MAP",
            {GeneratorName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                GeneratorName.PULSE1,
                {},
                FeatureKey.VOLUME,
                1,
            )

        reconstruction.update_generator_data.assert_not_called()


class TestRegenerationServiceCancellationConstraints:
    """Tests that document the non-preemptive cancellation behaviour.

    cancel() only prevents new tasks from starting. It does NOT interrupt
    synthesis that is already in progress.
    """

    def test_cancel_while_running_does_not_interrupt_synthesis(self, synthesis_mocks) -> None:
        service = RegenerationService()
        results: List[Any] = []
        done = threading.Event()

        def on_result(result: Any) -> None:
            results.append(result)
            done.set()

        service.subscribe(on_result)

        task_started = threading.Event()
        task_unblock = threading.Event()

        def blocking_from_features(features):
            task_started.set()
            task_unblock.wait(timeout=2.0)
            return [synthesis_mocks.instruction]

        synthesis_mocks.exporter.from_features.side_effect = blocking_from_features
        reconstruction = MagicMock()
        reconstruction.config = MagicMock()

        def run() -> None:
            service._run(reconstruction, synthesis_mocks.generator_name, {}, FeatureKey.VOLUME, 1)

        _real_executor_execute(service._executor, run, wait=False)
        task_started.wait(timeout=2.0)

        service.cancel()
        task_unblock.set()

        done.wait(timeout=2.0)

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_cancel_after_completion_prevents_new_tasks(self, synthesis_mocks, reconstruction) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service.start(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            1,
        )

        service.cancel()
        second_result = service.start(
            reconstruction,
            synthesis_mocks.generator_name,
            {},
            FeatureKey.VOLUME,
            2,
        )

        assert second_result is False


class TestRegenerationServiceHangingTask:
    """Tests that document the absence of a timeout mechanism.

    When the executor is occupied, start() is silently rejected.  There is no
    watchdog, retry, or escalation — the caller receives False and must decide
    what to do.  These tests use mocks so they remain fast and deterministic.
    """

    def test_no_result_emitted_when_executor_is_busy(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        with patch.object(service._executor, "execute", return_value=False):
            service.start(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock())

        assert results == []

    def test_start_rejected_indefinitely_while_busy(self) -> None:
        service = RegenerationService()

        with patch.object(service._executor, "execute", return_value=False):
            outcomes = [service.start(MagicMock(), MagicMock(), {}, MagicMock(), MagicMock()) for _ in range(5)]

        assert all(outcome is False for outcome in outcomes)

    def test_debounce_with_real_thread(self) -> None:
        """Second task is rejected while the first thread is alive (real threading)."""
        service = RegenerationService()
        block = threading.Event()
        task_started = threading.Event()

        def hanging() -> None:
            task_started.set()
            block.wait(timeout=5.0)

        _real_executor_execute(service._executor, hanging, wait=False)
        task_started.wait(timeout=1.0)

        second = _real_executor_execute(service._executor, lambda: None, wait=False)

        assert second is False

        block.set()
        if service._executor._thread is not None:
            service._executor._thread.join(timeout=1.0)
