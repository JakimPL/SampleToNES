from typing import Any, List
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.services.regeneration import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.enums import FeatureKey, GeneratorName

_real_queue_add = CallbackQueue.add

SCHEDULE_PRIORITY = 1
SETTLE_PRIORITY = 0

GENEROUS_BUDGET_SECONDS = 1.0
DELIVERY_BUDGET_FRAMES = 10
SETTLE_DELAY_FRAMES = 500


class TestRegenerationServicePipeline:
    """Full synthesis pipeline: real Config, Features (via PulseExporter), real PulseGenerator,
    and real Reconstruction.update_generator_data. Nothing is mocked.

    Tests call _run() directly to bypass the executor; the synchronous_executor fixture
    from the parent conftest covers start() in the final test.
    """

    def test_run_emits_service_success(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_run_emits_new_reconstruction_carrying_the_edit(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        emitted = results[0].value
        assert emitted.reconstruction is not reconstruction_data.reconstruction
        assert len(emitted.reconstruction.get_generator_approximation(GeneratorName.PULSE1)) > 0
        assert emitted.generator_name is GeneratorName.PULSE1
        assert emitted.feature_key is FeatureKey.VOLUME

    def test_run_updates_reconstruction_approximation(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        approximation = reconstruction_data.reconstruction.get_generator_approximation(GeneratorName.PULSE1)
        assert len(approximation) > 0

    def test_run_updates_reconstruction_instructions(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        instructions = reconstruction_data.reconstruction.get_generator_instructions(GeneratorName.PULSE1)
        assert len(instructions) > 0

    def test_run_feature_mutation_is_applied_before_synthesis(self, reconstruction_data, pulse_features) -> None:
        new_volume = np.zeros(len(pulse_features.volume), dtype=np.int8)
        service = RegenerationService()

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            new_volume,
        )

        assert (pulse_features.volume == new_volume).all()

    def test_run_emits_service_error_for_wrong_features_type(self, reconstruction_data) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            {},
            FeatureKey.VOLUME,
            np.zeros(4, dtype=np.int8),
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceError)

    def test_start_completes_through_full_pipeline(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service.start(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)


class TestRegenerationDeliveryThroughRealQueue:
    """Regression guard for the frame-gate starvation that froze reconstruction regeneration.

    After the parallelization rework, every background result reaches the main thread only through
    ``CallbackQueue.process``, drained once per render frame. ``process`` decides whether anything is
    due by inspecting the single heap-top task's target frame — correct only when the heap is ordered
    earliest-frame first. When ordering was priority-number first, a lower-priority-number task queued
    for a *future* frame (an in-flight pitch-stepper settle, a debounced tree/converter task) parked at
    the heap top and starved the due regeneration result behind it, so editing an instrument "did
    nothing". These tests drive the real queue end to end and would fail on that ordering.
    """

    @pytest.fixture(autouse=True)
    def real_queue(self):
        """Run these tests against the real ``CallbackQueue`` rather than the synchronous call-through.

        The parent conftest's autouse ``synchronous_queue`` swaps ``CallbackQueue.add`` for a direct
        call-through, which would deliver results inline and hide the frame-gate entirely. This pins the
        real heap-based ``add`` back on top of it and hands each test a clean, live queue, so delivery
        happens only when the test pumps ``notify_frame``/``process`` exactly as the render loop does.
        """
        with patch.object(CallbackQueue, "add", _real_queue_add):
            CallbackQueue.stop()
            CallbackQueue.start()
            yield
            CallbackQueue.stop()

    def test_result_delivered_despite_future_lower_priority_task(self, reconstruction_data, pulse_features) -> None:
        service = RegenerationService(priority=SCHEDULE_PRIORITY)
        results: List[Any] = []
        service.subscribe(results.append)

        # A co-pending settle-style task: a lower priority number, targeting a frame far beyond the
        # delivery window. Under the old priority-first ordering it sits at the heap top and blocks the
        # gate for every frame it remains pending.
        CallbackQueue.add(lambda: None, priority=SETTLE_PRIORITY, delay=SETTLE_DELAY_FRAMES)

        # The real synthesis emits its ServiceSuccess onto the real queue, due at the current frame.
        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            pulse_features.volume,
        )

        # The real queue defers delivery until a frame is pumped; nothing has run yet. This also fails
        # loudly if the synchronous call-through ever leaks through, so the test cannot pass trivially.
        assert results == []

        for _ in range(DELIVERY_BUDGET_FRAMES):
            CallbackQueue.notify_frame()
            CallbackQueue.process(GENEROUS_BUDGET_SECONDS)
            if results:
                break

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_edit_reaches_subscriber_within_frame_budget(self, reconstruction_data, pulse_features) -> None:
        """The reported symptom, stated positively: an edit's regenerated reconstruction reaches the
        subscriber promptly even while a lower-priority settle is pending."""
        service = RegenerationService(priority=SCHEDULE_PRIORITY)
        delivered: List[Any] = []
        service.subscribe(delivered.append)

        CallbackQueue.add(lambda: None, priority=SETTLE_PRIORITY, delay=SETTLE_DELAY_FRAMES)

        new_volume = np.zeros(len(pulse_features.volume), dtype=np.int8)
        service._run(
            reconstruction_data.reconstruction,
            GeneratorName.PULSE1,
            pulse_features,
            FeatureKey.VOLUME,
            new_volume,
        )

        for _ in range(DELIVERY_BUDGET_FRAMES):
            CallbackQueue.notify_frame()
            CallbackQueue.process(GENEROUS_BUDGET_SECONDS)
            if delivered:
                break

        assert len(delivered) == 1
        regenerated = delivered[0].value
        assert regenerated.reconstruction is not reconstruction_data.reconstruction
        assert regenerated.generator_name is GeneratorName.PULSE1
        assert regenerated.feature_key is FeatureKey.VOLUME
