import threading
from types import SimpleNamespace
from typing import Any, Callable, Dict, Final, Iterator, List, Tuple, TypeAlias, cast
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.services.result import (
    ServiceCanceled,
    ServiceError,
    ServiceSuccess,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.exporters import Features
from sampletones_core.features.envelope import Envelope
from sampletones_core.reconstructions import Reconstruction
from tests.conftest import ReconstructionFactory

REFERENCE_PITCH: Final[int] = 60

MockReconstruction: TypeAlias = MagicMock
SynthesisMocks: TypeAlias = SimpleNamespace
ResultCallback: TypeAlias = Callable[[Any], None]


@pytest.fixture
def features() -> Features:
    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=Envelope[int](items=(15, 0)),
        arpeggio=Envelope[int](items=(0, 0)),
        pitch=None,
        hi_pitch=None,
        duty_cycle=Envelope[int](items=(0, 0)),
    )


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
        "sampletones_application.services.regeneration.service.CHANNEL_TO_EXPORTER_MAP",
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
    def test_start_when_not_canceled_returns_true(
        self, synthesis_mocks: SynthesisMocks, reconstruction: MockReconstruction
    ) -> None:
        service = RegenerationService()
        result = service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            FeatureKey.VOLUME,
            cast(Features, {}),
        )
        assert result is True

    def test_start_when_canceled_returns_false(self) -> None:
        service = RegenerationService()
        service.cancel()

        result = service.start(MagicMock(), MagicMock(), FeatureKey.VOLUME, cast(Features, {}))

        assert result is False

    def test_start_when_canceled_does_not_emit(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service.cancel()

        service.start(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            cast(Features, {}),
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
                MagicMock(),
                cast(Features, {}),
            )

        assert result is False

    def test_cancel_sets_canceled_flag(self) -> None:
        service = RegenerationService()
        assert not service._canceled

        service.cancel()

        assert service._canceled


class TestRegenerationServiceIsRunning:
    def test_is_running_delegates_to_the_executor(self) -> None:
        service = RegenerationService()
        service._executor = MagicMock()

        service._executor.is_running = True
        assert service.is_running() is True

        service._executor.is_running = False
        assert service.is_running() is False


class TestRegenerationServiceRun:
    def test_run_when_canceled_emits_service_canceled(self) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        service._canceled = True

        service._run(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            cast(Features, {}),
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceCanceled)

    def test_run_success_emits_service_success(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            FeatureKey.VOLUME,
            features,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
        outcome = results[0].value
        assert outcome.reconstruction is reconstruction.model_copy.return_value
        assert outcome.reconstruction is not reconstruction
        assert outcome.channel_name is synthesis_mocks.channel_name
        assert outcome.feature_key is FeatureKey.VOLUME

    def test_run_regenerates_from_the_envelopes_it_is_handed(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """The caller writes the edit into the envelopes, so the service renders what it is given."""
        service = RegenerationService()

        service._run(reconstruction, synthesis_mocks.channel_name, FeatureKey.VOLUME, features)

        _, _, _, initial_pitch, held = reconstruction.model_copy.return_value.update_channel_data.call_args.args
        assert initial_pitch == features.initial_pitch
        assert held == features.held_features

    def test_run_updates_reconstruction_copy(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            FeatureKey.VOLUME,
            features,
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
        features: Features,
    ) -> None:
        """An arpeggio edit stores the reference pitch the edit was made from.

        Handing the unchanged reference back to the reconstruction is what keeps a later
        export measuring the envelope against the same base.
        """
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            FeatureKey.ARPEGGIO,
            features,
        )

        call_args = reconstruction.model_copy.return_value.update_channel_data.call_args
        assert call_args.args[3] == REFERENCE_PITCH

    def test_run_carries_a_moved_reference_pitch(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """The pitch stepper's edit reaches the reconstruction as the reference it stores."""
        moved = features.model_copy(update={"initial_pitch": REFERENCE_PITCH + 12})
        service = RegenerationService()

        service._run(reconstruction, synthesis_mocks.channel_name, FeatureKey.INITIAL_PITCH, moved)

        _, _, _, initial_pitch, _ = reconstruction.model_copy.return_value.update_channel_data.call_args.args
        assert initial_pitch == REFERENCE_PITCH + 12

    def test_run_calls_generator_for_each_instruction(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
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
            FeatureKey.VOLUME,
            features,
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
            "sampletones_application.services.regeneration.service.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                FeatureKey.VOLUME,
                cast(Features, {}),
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
            "sampletones_application.services.regeneration.service.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                FeatureKey.VOLUME,
                cast(Features, {}),
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
        features = reconstruction.export()[ChannelName.PULSE1].leave_to_channel(
            [FeatureKey.VOLUME, FeatureKey.ARPEGGIO, FeatureKey.DUTY_CYCLE]
        )
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            ChannelName.PULSE1,
            FeatureKey.VOLUME,
            features,
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
    """Tests that document the non-preemptive cancellation behavior.

    cancel() only prevents new tasks from starting. It does NOT interrupt
    synthesis that is already in progress.
    """

    def test_cancel_while_running_does_not_interrupt_synthesis(
        self,
        synthesis_mocks: SynthesisMocks,
        features: Features,
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
                FeatureKey.VOLUME,
                features,
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
            FeatureKey.VOLUME,
            cast(Features, {}),
        )

        service.cancel()
        second_result = service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            FeatureKey.VOLUME,
            cast(Features, {}),
        )

        assert second_result is False
