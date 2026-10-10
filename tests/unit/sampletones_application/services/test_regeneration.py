from types import SimpleNamespace
from typing import Any, Callable, Dict, Final, FrozenSet, Iterator, List, Tuple, TypeAlias, cast
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sampletones_application.services.regeneration import service as service_module
from sampletones_application.services.regeneration.result import RegeneratedInstrument
from sampletones_application.services.regeneration.service import RegenerationService
from sampletones_application.services.result import (
    ServiceError,
    ServiceSuccess,
)
from sampletones_application.utils.parallelization.thread import SingleThreadExecutor
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.exporters import Features
from sampletones_core.features import CHANNEL_GENERATOR_KIND, supported_features
from sampletones_core.features.envelope import Envelope
from sampletones_core.instructions import InstructionUnion
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.renders import rendered_channels, rendered_mix
from tests.conftest import ReconstructionFactory
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, taking_turns

__all__ = ["taking_turns"]

REFERENCE_PITCH: Final[int] = 60
NO_RENDERS: Final[Dict[ChannelName, np.ndarray]] = {}

MockReconstruction: TypeAlias = MagicMock
SynthesisMocks: TypeAlias = SimpleNamespace
EVERY_STEM: Final[FrozenSet[int]] = frozenset({0})
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
    reconstruction.with_channel_data.return_value.instructions_data = ()
    return reconstruction


class TestRegenerationServiceStart:
    def test_start_runs_the_rebuild_on_the_worker(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """The worker runs the job it is handed, and its result reaches the subscriber."""
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service.start(
            reconstruction,
            synthesis_mocks.channel_name,
            features,
            EVERY_STEM,
            kept=NO_RENDERS,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)

    def test_a_job_started_as_the_last_one_winds_down_still_runs(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """One job runs at a time, and a job started while the worker winds down runs once it has.

        The rewrites start the next rebuild as the previous result arrives, so every start is
        answered and the line moves on.
        """
        service = RegenerationService()
        with patch.object(service._executor, "execute") as execute:
            service.start(reconstruction, synthesis_mocks.channel_name, features, EVERY_STEM, kept=NO_RENDERS)

        assert execute.call_args.kwargs == {"wait": True}


class TestRegenerationServiceRun:
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
            features,
            EVERY_STEM,
            NO_RENDERS,
        )

        assert len(results) == 1
        assert isinstance(results[0], ServiceSuccess)
        outcome = results[0].value
        assert outcome.reconstruction is reconstruction.with_channel_data.return_value
        assert outcome.reconstruction is not reconstruction

    def test_run_regenerates_from_the_envelopes_it_is_handed(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """The caller writes the edit into the envelopes, so the service renders what it is given."""
        service = RegenerationService()

        service._run(reconstruction, synthesis_mocks.channel_name, features, EVERY_STEM, NO_RENDERS)

        _, _, initial_pitch, held = reconstruction.with_channel_data.call_args.args
        assert initial_pitch == features.initial_pitch
        assert held == features.held_features

    def test_run_asks_the_document_for_its_edited_channel(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            features,
            EVERY_STEM,
            NO_RENDERS,
        )

        reconstruction.with_channel_data.assert_called_once()
        call_args = reconstruction.with_channel_data.call_args
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
            features,
            EVERY_STEM,
            NO_RENDERS,
        )

        call_args = reconstruction.with_channel_data.call_args
        assert call_args.args[2] == REFERENCE_PITCH

    def test_run_carries_a_moved_reference_pitch(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        """The pitch stepper's edit reaches the reconstruction as the reference it stores."""
        moved = features.model_copy(update={"initial_pitch": REFERENCE_PITCH + 12})
        service = RegenerationService()

        service._run(reconstruction, synthesis_mocks.channel_name, moved, EVERY_STEM, NO_RENDERS)

        _, _, initial_pitch, _ = reconstruction.with_channel_data.call_args.args
        assert initial_pitch == REFERENCE_PITCH + 12

    def test_run_hands_on_every_instruction_the_envelopes_describe(
        self,
        synthesis_mocks: SynthesisMocks,
        reconstruction: MockReconstruction,
        features: Features,
    ) -> None:
        extra_instruction = MagicMock()
        stream = [synthesis_mocks.instruction, extra_instruction]
        synthesis_mocks.exporter.from_features.return_value = stream
        service = RegenerationService()

        service._run(
            reconstruction,
            synthesis_mocks.channel_name,
            features,
            EVERY_STEM,
            NO_RENDERS,
        )

        call_args = reconstruction.with_channel_data.call_args
        assert call_args.args[1] == stream

    def test_run_exception_emits_service_error(
        self,
        reconstruction: MockReconstruction,
    ) -> None:
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        exception = RuntimeError("synthesis failed")
        mock_exporter = MagicMock()
        mock_exporter.from_features.side_effect = exception

        with patch(
            "sampletones_application.services.regeneration.service.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                cast(Features, {}),
                EVERY_STEM,
                NO_RENDERS,
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
        mock_exporter.from_features.side_effect = RuntimeError("fail")

        with patch(
            "sampletones_application.services.regeneration.service.CHANNEL_TO_EXPORTER_MAP",
            {ChannelName.PULSE1: mock_exporter},
        ):
            service._run(
                reconstruction,
                ChannelName.PULSE1,
                cast(Features, {}),
                EVERY_STEM,
                NO_RENDERS,
            )

        reconstruction.with_channel_data.assert_not_called()


class TestClearingEveryEnvelope:
    """An instrument left with no envelope at all describes no frame, so its channel stands by.

    This is the edit the instruments panel offers on the last dimension an instrument writes, and
    it runs the whole way through the service: the exporter produces no instruction, the render
    produces no audio, and the reconstruction that comes back holds the channel without playing it.
    """

    @staticmethod
    def _regenerated(reconstruction: Reconstruction) -> Reconstruction:
        """The reconstruction the service returns once every dimension is left to the channel."""
        exported = reconstruction.export()[ChannelName.PULSE1]
        features = exported.leave_to_channel(exported.envelopes)
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)

        service._run(
            reconstruction,
            ChannelName.PULSE1,
            features,
            EVERY_STEM,
            NO_RENDERS,
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

        assert rendered_channels(regenerated) == {}
        assert rendered_mix(regenerated).size == 0

    def test_the_cleared_channel_records_every_dimension_as_the_channels(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        regenerated = self._regenerated(reconstruction)

        assert regenerated.held_features[ChannelName.PULSE1] == tuple(
            supported_features(CHANNEL_GENERATOR_KIND[ChannelName.PULSE1])
        )
        assert not regenerated.export()[ChannelName.PULSE1].has_frames

    def test_the_reconstruction_the_edit_was_made_from_keeps_playing(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        reconstruction = reconstruction_factory()

        self._regenerated(reconstruction)

        assert reconstruction.playing_channels == (ChannelName.PULSE1,)


def _never_rendering(
    instructions: List[InstructionUnion],
    channel_name: ChannelName,
    config: Config,
) -> np.ndarray:
    raise AssertionError(f"{channel_name} was rendered")


def _rebuilt(reconstruction: Reconstruction, kept: Dict[ChannelName, np.ndarray]) -> RegeneratedInstrument:
    """What the service reports once it rebuilds the shared channel of ``reconstruction`` from its own envelopes."""
    service = RegenerationService()
    results: List[Any] = []
    service.subscribe(results.append)

    service._run(
        reconstruction,
        SHARED_CHANNEL,
        reconstruction.export()[SHARED_CHANNEL],
        reconstruction.recorded_stem_ids,
        kept,
    )

    assert isinstance(results[0], ServiceSuccess)
    outcome: RegeneratedInstrument = results[0].value
    return outcome


class TestWhatTheRebuildSounds:
    """The result carries the audio of every channel in play: the rebuilt channel rendered afresh, and a
    render handed in carried over for a channel the edit left alone.

    A channel the edit leaves alone keeps its stream, so the render the caller holds for it is the
    render of the rebuilt document too. A render handed for the rebuilt channel sounds the stream
    the edit replaced, so the worker renders that channel whatever it was handed.
    """

    def test_the_rebuilt_channel_and_the_mix_are_rendered(self, taking_turns: Reconstruction) -> None:
        outcome = _rebuilt(taking_turns, NO_RENDERS)

        expected = rendered_channels(outcome.reconstruction)
        assert outcome.channels.keys() == expected.keys()
        assert all(np.array_equal(outcome.channels[name], expected[name]) for name in expected)
        assert np.array_equal(outcome.mix, rendered_mix(outcome.reconstruction))

    def test_a_render_handed_for_a_channel_left_alone_carries_over(
        self,
        taking_turns: Reconstruction,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        handed = rendered_channels(taking_turns)
        rendered: List[ChannelName] = []
        real_render = service_module.render_instructions
        monkeypatch.setattr(
            service_module,
            "render_instructions",
            lambda instructions, channel_name, config: rendered.append(channel_name)
            or real_render(instructions, channel_name, config),
        )

        outcome = _rebuilt(taking_turns, {SOLE_CHANNEL: handed[SOLE_CHANNEL]})

        assert outcome.channels[SOLE_CHANNEL] is handed[SOLE_CHANNEL]
        assert rendered == [SHARED_CHANNEL]

    def test_a_channel_handed_no_render_is_rendered(self, taking_turns: Reconstruction) -> None:
        outcome = _rebuilt(taking_turns, NO_RENDERS)

        assert np.array_equal(outcome.channels[SOLE_CHANNEL], rendered_channels(taking_turns)[SOLE_CHANNEL])

    def test_a_render_handed_for_the_rebuilt_channel_is_passed_over(self, taking_turns: Reconstruction) -> None:
        stale = rendered_channels(taking_turns)[SHARED_CHANNEL]

        outcome = _rebuilt(taking_turns, {SHARED_CHANNEL: stale})

        assert outcome.channels[SHARED_CHANNEL] is not stale


class TestAShutdownMidRebuild:
    """A shutdown asked for while a rebuild runs ends the job with no render and no report.

    The queue the report would reach is being stopped with the shutdown, so the job lets its result
    go and the worker is joined the sooner.
    """

    @pytest.fixture(autouse=True)
    def armed_again(self) -> Iterator[None]:
        yield
        SingleThreadExecutor.reset_shutdown()

    def test_the_job_renders_nothing_and_reports_nothing(
        self,
        taking_turns: Reconstruction,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(service_module, "render_instructions", _never_rendering)
        service = RegenerationService()
        results: List[Any] = []
        service.subscribe(results.append)
        SingleThreadExecutor.request_shutdown()

        service._run(
            taking_turns,
            SHARED_CHANNEL,
            taking_turns.export()[SHARED_CHANNEL],
            taking_turns.recorded_stem_ids,
            NO_RENDERS,
        )

        assert results == []
