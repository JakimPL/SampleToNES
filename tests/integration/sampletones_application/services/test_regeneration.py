from dataclasses import dataclass, field
from typing import Any, List
from unittest.mock import patch

import numpy as np
import pytest

from sampletones_application.logic.reconstruction.feature import FeatureData
from sampletones_application.services.regeneration import RegenerationService
from sampletones_application.services.result import ServiceError, ServiceSuccess
from sampletones_application.utils.callbacks.queue import CallbackQueue
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from tests.suite.scenario import BaseTestScenario, ScenarioStep

_real_queue_add = CallbackQueue.add

SCHEDULE_PRIORITY = 1
SETTLE_PRIORITY = 0

GENEROUS_BUDGET_SECONDS = 1.0
DELIVERY_BUDGET_FRAMES = 10
SETTLE_DELAY_FRAMES = 500

BASE_PITCH = 60
OCTAVE = 12


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
        assert len(emitted.reconstruction.approximations.get(GeneratorName.PULSE1, np.array([], dtype=np.float32))) > 0
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

        approximation = reconstruction_data.reconstruction.approximations.get(
            GeneratorName.PULSE1, np.array([], dtype=np.float32)
        )
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


@dataclass
class ArpeggioEditContext:
    reconstruction: Reconstruction
    features: Features
    history: List[List[int]] = field(default_factory=list)


def _edit_arpeggio(context: ArpeggioEditContext, arpeggio: np.ndarray) -> None:
    """Applies an arpeggio envelope through the real regeneration pipeline.

    Each edit runs on its own service, exactly as the instruments panel drives one, and the
    regenerated reconstruction replaces the context's own so the next edit continues from it.
    """
    service = RegenerationService()
    results: List[Any] = []
    service.subscribe(results.append)

    service._run(
        context.reconstruction,
        GeneratorName.PULSE1,
        context.features,
        FeatureKey.ARPEGGIO,
        arpeggio,
    )

    assert len(results) == 1
    assert isinstance(results[0], ServiceSuccess)
    context.reconstruction = results[0].value.reconstruction
    context.history.append(_pitches(context))


def _pitches(context: ArpeggioEditContext) -> List[int]:
    instructions = context.reconstruction.get_generator_instructions(GeneratorName.PULSE1)
    return [instruction.pitch for instruction in instructions]


class TestArpeggioEditKeepsTheSamplePitch:
    """The reported bug, end to end on the real pipeline.

    Typing an arpeggio envelope into a channel and clearing it again sounds the sample at the
    note it was reconstructed at. The reference pitch travels with the instructions each edit
    produces, so the second edit measures its offsets from the base the first one started at.
    """

    def test_clearing_an_arpeggio_returns_the_sample_to_its_pitch(self, reconstruction_data) -> None:
        def build() -> ArpeggioEditContext:
            reconstruction = reconstruction_data.reconstruction
            return ArpeggioEditContext(
                reconstruction=reconstruction,
                features=FeatureData.load(reconstruction)[GeneratorName.PULSE1],
            )

        def check_the_starting_reference(context: ArpeggioEditContext) -> None:
            assert context.features.initial_pitch == BASE_PITCH
            assert context.features.arpeggio.tolist() == [0]

        def raise_the_first_frame_an_octave(context: ArpeggioEditContext) -> None:
            _edit_arpeggio(context, np.array([OCTAVE, 0, 0, 0], dtype=np.int8))
            assert _pitches(context) == [BASE_PITCH + OCTAVE] + [BASE_PITCH] * 3

        def reload_the_edited_features(context: ArpeggioEditContext) -> None:
            context.features = FeatureData.load(context.reconstruction)[GeneratorName.PULSE1]
            assert context.features.initial_pitch == BASE_PITCH
            assert context.features.arpeggio.tolist() == [OCTAVE, 0]

        def clear_the_envelope(context: ArpeggioEditContext) -> None:
            _edit_arpeggio(context, np.zeros(len(context.features.arpeggio), dtype=np.int8))
            assert _pitches(context) == [BASE_PITCH] * 4

        def check_the_reference_held(context: ArpeggioEditContext) -> None:
            reloaded = FeatureData.load(context.reconstruction)[GeneratorName.PULSE1]
            assert reloaded.initial_pitch == BASE_PITCH
            assert reloaded.arpeggio.tolist() == [0]

        scenario = BaseTestScenario(
            label="arpeggio_edit_keeps_the_sample_pitch",
            build=build,
            steps=[
                ScenarioStep(label="check_the_starting_reference", action=check_the_starting_reference),
                ScenarioStep(label="raise_the_first_frame_an_octave", action=raise_the_first_frame_an_octave),
                ScenarioStep(label="reload_the_edited_features", action=reload_the_edited_features),
                ScenarioStep(label="clear_the_envelope", action=clear_the_envelope),
                ScenarioStep(label="check_the_reference_held", action=check_the_reference_held),
            ],
        )

        context = scenario.run()

        assert context.history[-1] == [BASE_PITCH] * 4


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
