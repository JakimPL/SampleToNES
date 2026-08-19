import threading
from types import SimpleNamespace
from typing import Any, Callable, Dict, Final, Iterator, List, Tuple, TypeAlias, cast
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.services.regeneration import RegenerationService
from sampletones_application.services.result import (
    ServiceCancelled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.reconstructions import Reconstruction
from tests.conftest import ReconstructionFactory

REFERENCE_PITCH: Final[int] = 60

MockReconstruction: TypeAlias = MagicMock
SynthesisMocks: TypeAlias = SimpleNamespace
ResultCallback: TypeAlias = Callable[[Any], None]


class FakeFeatures(Dict[Any, Any]):
    """Stands in for ``Features``: records the edited dimension and carries a reference pitch.

    Assigning ``FeatureKey.INITIAL_PITCH`` moves the reference pitch, matching the real model,
    so the pitch stepper's edit is observable through ``initial_pitch``. The dimensions left to
    the channel are read the same way the real model reports them: those whose envelope is empty.
    """

    def __init__(self, initial_pitch: int) -> None:
        super().__init__()
        self.initial_pitch = initial_pitch

    @property
    def held_features(self) -> Tuple[FeatureKey, ...]:
        return tuple(key for key, value in self.items() if isinstance(value, np.ndarray) and value.size == 0)

    def __setitem__(self, feature_key: Any, value: Any) -> None:
        if feature_key == FeatureKey.INITIAL_PITCH:
            self.initial_pitch = value
        else:
            super().__setitem__(feature_key, value)


@pytest.fixture
def features() -> FakeFeatures:
    return FakeFeatures(REFERENCE_PITCH)


@pytest.fixture
def synthesis_mocks() -> Iterator[SynthesisMocks]:
    mock_instruction = MagicMock()
    mock_exporter = MagicMock()
    mock_generator_class = MagicMock()
    mock_generator = MagicMock(return_value=np.zeros(100))

    mock_generator_class.return_value = mock_generator
    mock_exporter.get_generator_type.return_value = mock_generator_class
    mock_exporter.from_features.return_value = [mock_instruction]

    channel_name = ChannelName.PULSE1

    with patch(
        "sampletones_application.services.regeneration.CHANNEL_TO_EXPORTER_MAP",
        {channel_name: mock_exporter},
    ):
        yield SimpleNamespace(
            exporter=mock_exporter,
            generator_class=mock_generator_class,
            generator=mock_generator,
            instruction=mock_instruction,
            channel_name=channel_name,
        )


@pytest.fixture
def reconstruction() -> MockReconstruction:
    reconstruction = MagicMock()
    reconstruction.config = MagicMock()
    return reconstruction


class TestRegenerationServiceStart:
    def test_start_when_not_cancelled_returns_true(
        self, synthesis_mocks: SynthesisMocks, reconstruction: MockReconstruction
    ) -> None:
        service = RegenerationService()
        result = service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, {}),
            FeatureKey.VOLUME,
            1,
        )
        assert result is True

    def test_start_when_cancelled_returns_false(self) -> None:
        service = RegenerationService()
        service.cancel()

        result = service.start(MagicMock(), MagicMock(), cast(Features, {}), MagicMock(), MagicMock())

        assert result is False

    def test_start_when_cancelled_does_not_emit(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service.cancel()

        service.start(
            MagicMock(),
            MagicMock(),
            cast(Features, {}),
            MagicMock(),
            MagicMock(),
        )

        assert results == []

    def test_start_reports_a_submit_failure(self) -> None:
        """``start`` propagates the executor's accepted/rejected verdict.

        The coalescing worker owns the launch; ``start`` merely forwards whether the
        submission was accepted, so a caller can gate on it.
        """
        service = RegenerationService()
        with patch.object(service._executor, "submit", return_value=False):
            result = service.start(
                MagicMock(),
                MagicMock(),
                cast(Features, {}),
                MagicMock(),
                MagicMock(),
            )

        assert result is False

    def test_cancel_sets_cancelled_flag(self) -> None:
        service = RegenerationService()
        assert not service._cancelled

        service.cancel()

        assert service._cancelled


class TestRegenerationServiceIsRunning:
    def test_is_running_delegates_to_the_executor(self) -> None:
        service = RegenerationService()
        service._executor = MagicMock()

        service._executor.is_running = True
        assert service.is_running() is True

        service._executor.is_running = False
        assert service.is_running() is False


class TestRegenerationServiceRun:
    def test_run_when_cancelled_emits_service_cancelled(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service._cancelled = True

        service._run(
            MagicMock(),
            MagicMock(),
            cast(Features, {}),
            MagicMock(),
            MagicMock(),
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceCancelled)

    def test_run_success_emits_service_success(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            FeatureKey.VOLUME,
            1,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
        outcome = results[0].value
        assert outcome.reconstruction is reconstruction.model_copy.return_value
        assert outcome.reconstruction is not reconstruction
        assert outcome.channel_name is synthesis_mocks.channel_name
        assert outcome.feature_key is FeatureKey.VOLUME

    def test_run_updates_feature_before_synthesis(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        service = RegenerationService()
        feature_key = FeatureKey.VOLUME
        new_value = 42

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            feature_key,
            new_value,
        )

        assert features[feature_key] == new_value

    def test_run_updates_reconstruction_copy(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            FeatureKey.VOLUME,
            1,
        )

        updated = reconstruction.model_copy.return_value
        updated.update_channel_data.assert_called_once()
        reconstruction.update_channel_data.assert_not_called()
        call_args = updated.update_channel_data.call_args
        assert call_args.args[0] == synthesis_mocks.channel_name

    def test_run_carries_the_reference_pitch_through_an_arpeggio_edit(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        """An arpeggio edit stores the reference pitch the edit was made from.

        Handing the unchanged reference back to the reconstruction is what keeps a later
        export measuring the envelope against the same base.
        """
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            FeatureKey.ARPEGGIO,
            np.array([12, 0], dtype=np.int8),
        )

        call_args = reconstruction.model_copy.return_value.update_channel_data.call_args
        assert call_args.args[3] == REFERENCE_PITCH

    def test_run_carries_a_moved_reference_pitch(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        """The pitch stepper's edit stores the new reference pitch."""
        moved_pitch = REFERENCE_PITCH + 12
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            FeatureKey.INITIAL_PITCH,
            moved_pitch,
        )

        call_args = reconstruction.model_copy.return_value.update_channel_data.call_args
        assert call_args.args[3] == moved_pitch

    def test_run_calls_generator_for_each_instruction(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: FakeFeatures,
    ) -> None:
        extra_instruction = MagicMock()
        synthesis_mocks.exporter.from_features.return_value = [
            synthesis_mocks.instruction,
            extra_instruction,
        ]
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, features),
            FeatureKey.VOLUME,
            1,
        )

        assert synthesis_mocks.generator.call_count == 2

    def test_run_exception_emits_service_error(
        self,
        reconstruction: MockReconstruction,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        exception = RuntimeError("synthesis failed")
        mock_exporter = MagicMock()
        mock_exporter.get_generator_type.side_effect = exception

        with patch(
            "sampletones_application.services.regeneration.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                cast(Features, {}),
                FeatureKey.VOLUME,
                1,
            )

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, ServiceError)
        assert result.exception is exception

    def test_run_exception_does_not_update_reconstruction(
        self,
        reconstruction: MockReconstruction,
    ) -> None:
        service = RegenerationService()
        mock_exporter = MagicMock()
        mock_exporter.get_generator_type.side_effect = RuntimeError("fail")

        with patch(
            "sampletones_application.services.regeneration.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                cast(Features, {}),
                FeatureKey.VOLUME,
                1,
            )

        reconstruction.update_channel_data.assert_not_called()


class TestClearingEveryEnvelope:
    """An instrument left with no envelope at all describes no frame, so its channel stands by.

    This is the edit the instruments panel offers on the last dimension an instrument writes, and
    it runs the whole way through the service: the exporter produces no instruction, the render
    produces no audio, and the reconstruction that comes back holds the channel without playing it.
    """

    @staticmethod
    def _regenerated(reconstruction: Reconstruction) -> Reconstruction:
        """The reconstruction the service returns once every dimension is left to the channel."""
        features = reconstruction.export()[ChannelName.PULSE1]
        features.leave_to_channel([FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE])
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            ChannelName.PULSE1,
            features,
            FeatureKey.VOLUME,
            np.array([], dtype=np.int8),
        )

        assert isinstance(results[0], ServiceSuccess)
        regenerated: Reconstruction = results[0].value.reconstruction
        return regenerated

    def test_a_cleared_instrument_takes_its_channel_out_of_play(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        regenerated = self._regenerated(reconstruction)

        assert regenerated.instructions[ChannelName.PULSE1] == []
        assert regenerated.playing_channels == ()

    def test_a_cleared_instrument_sounds_as_an_empty_waveform(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        regenerated = self._regenerated(reconstruction)

        assert regenerated.approximations == {}
        assert regenerated.approximation.size == 0

    def test_the_cleared_channel_records_every_dimension_as_the_channels(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        regenerated = self._regenerated(reconstruction)

        assert regenerated.held_features[ChannelName.PULSE1] == (
            FeatureKey.VOLUME,
            FeatureKey.ARPEGGIO,
            FeatureKey.DUTY_CYCLE,
        )
        assert not regenerated.export()[ChannelName.PULSE1].has_frames

    def test_the_reconstruction_the_edit_was_made_from_keeps_playing(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        self._regenerated(reconstruction)

        assert reconstruction.playing_channels == (ChannelName.PULSE1,)


class TestRegenerationServiceCancellationConstraints:
    """Tests that document the non-preemptive cancellation behaviour.

    cancel() only prevents new tasks from starting. It does NOT interrupt
    synthesis that is already in progress.
    """

    def test_cancel_while_running_does_not_interrupt_synthesis(
        self,
        synthesis_mocks: SynthesisMocks,
        features: FakeFeatures,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        done = threading.Event()

        def on_result(result: Any) -> None:
            results.append(result)
            done.set()

        service.subscribe(on_result)

        task_started = threading.Event()
        task_unblock = threading.Event()

        def blocking_from_features(edited_features: Any) -> List[MagicMock]:
            task_started.set()
            task_unblock.wait(timeout=2.0)
            return [synthesis_mocks.instruction]

        synthesis_mocks.exporter.from_features.side_effect = blocking_from_features
        reconstruction = MagicMock()
        reconstruction.config = MagicMock()

        thread = threading.Thread(
            target=lambda: service._run(
                reconstruction,
                synthesis_mocks.channel_name,
                cast(Features, features),
                FeatureKey.VOLUME,
                1,
            ),
        )
        thread.start()
        task_started.wait(timeout=2.0)

        service.cancel()
        task_unblock.set()

        done.wait(timeout=2.0)
        thread.join(timeout=2.0)

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_cancel_after_completion_prevents_new_tasks(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, {}),
            FeatureKey.VOLUME,
            1,
        )

        service.cancel()
        second_result = service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            cast(Features, {}),
            FeatureKey.VOLUME,
            2,
        )

        assert second_result is False
