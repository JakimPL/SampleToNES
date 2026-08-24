from typing import Final, List, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance.audition import audition_audio
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_shared.exceptions import PlaybackError

REFERENCE_PITCH: Final[int] = 60
REFERENCE_PERIOD: Final[int] = 8
OCTAVE: Final[int] = 2
MIDDLE_C: Final[int] = 48
SEMITONE_G: Final[int] = 7


class _Editor:
    """A tab holding one instrument, or none, which is all an audition reads of it."""

    def __init__(self, instrument: Optional[Instrument]) -> None:
        self._instrument = instrument

    @property
    def instrument(self) -> Optional[Instrument]:
        return self._instrument


def _instrument() -> Instrument:
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 12)),
            arpeggio=Envelope[int](items=(0, 4)),
            duty_cycle=Envelope[int](items=(2,)),
        ),
        initial_pitch=REFERENCE_PITCH,
        initial_period=REFERENCE_PERIOD,
    )


@pytest.fixture
def controller() -> ProjectController:
    return ProjectController(ProjectManager())


@pytest.fixture
def session() -> MagicMock:
    manager = MagicMock(spec=SessionManager)
    manager.octave = OCTAVE
    return manager


@pytest.fixture
def device() -> MagicMock:
    return MagicMock(spec=AudioDeviceManager)


def _logic(
    instrument: Optional[Instrument],
    controller: ProjectController,
    session: MagicMock,
    device: MagicMock,
) -> InstrumentAuditionLogic:
    return InstrumentAuditionLogic(_Editor(instrument), controller, session, device)


def _played(device: MagicMock) -> np.ndarray:
    audio = device.play.call_args.args[0]
    assert isinstance(audio, np.ndarray)
    return audio


def _expected(
    instrument: Instrument,
    controller: ProjectController,
    channel_name: ChannelName,
    pitch: int,
) -> np.ndarray:
    settings = controller.project.settings
    config = Config().with_library(
        nes_frequency=settings.nes_frequency,
        sample_rate=settings.sample_rate,
    )
    audio = audition_audio(instrument, channel_name, config, pitch=pitch)
    assert audio is not None
    return audio


class TestWhatAKeySounds:
    def test_a_key_sounds_the_voice_at_the_note_it_names(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        instrument = _instrument()

        _logic(instrument, controller, session, device).sound(GeneratorName.PULSE, SEMITONE_G)

        expected = _expected(instrument, controller, ChannelName.PULSE1, MIDDLE_C + SEMITONE_G)
        assert np.array_equal(_played(device), expected)

    def test_the_octave_in_force_moves_the_note_the_same_key_sounds(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        instrument = _instrument()
        session.octave = OCTAVE + 1

        _logic(instrument, controller, session, device).sound(GeneratorName.PULSE, SEMITONE_G)

        expected = _expected(instrument, controller, ChannelName.PULSE1, MIDDLE_C + 12 + SEMITONE_G)
        assert np.array_equal(_played(device), expected)

    def test_the_generator_chosen_is_the_channel_the_voice_is_heard_on(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        instrument = _instrument()

        _logic(instrument, controller, session, device).sound(GeneratorName.TRIANGLE, SEMITONE_G)

        expected = _expected(instrument, controller, ChannelName.TRIANGLE, MIDDLE_C + SEMITONE_G)
        assert np.array_equal(_played(device), expected)

    def test_the_noise_generator_sounds_at_the_period_the_voice_states(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        """The noise channel selects one of sixteen periods, so a key there names no note."""
        instrument = _instrument()
        logic = _logic(instrument, controller, session, device)

        logic.sound(GeneratorName.NOISE, SEMITONE_G)
        first = _played(device)
        logic.sound(GeneratorName.NOISE, 0)
        second = _played(device)

        expected = _expected(instrument, controller, ChannelName.NOISE, REFERENCE_PERIOD)
        assert np.array_equal(first, expected)
        assert np.array_equal(second, expected)

    def test_an_audition_yields_to_the_playback_a_reader_asked_for(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        _logic(_instrument(), controller, session, device).sound(GeneratorName.PULSE, SEMITONE_G)

        assert device.play.call_args.kwargs["priority"] is PlaybackPriority.PREVIEW


class TestWhenNothingSounds:
    def test_a_tab_holding_no_instrument_plays_nothing(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        _logic(None, controller, session, device).sound(GeneratorName.PULSE, SEMITONE_G)

        device.play.assert_not_called()

    def test_a_voice_writing_no_envelope_plays_nothing(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        _logic(Instrument(name="silent"), controller, session, device).sound(
            GeneratorName.PULSE,
            SEMITONE_G,
        )

        device.play.assert_not_called()

    def test_a_device_refusing_the_audition_reports_what_it_refused_with(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        refusal = PlaybackError("no device")
        device.play.side_effect = refusal
        logic = _logic(_instrument(), controller, session, device)
        reported: List[Exception] = []
        logic.on_audition_error = reported.append

        logic.sound(GeneratorName.PULSE, SEMITONE_G)

        assert reported == [refusal]
