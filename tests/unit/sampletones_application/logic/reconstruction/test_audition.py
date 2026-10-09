from typing import Final, List, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.constants.instruments import AUDITION_GENERATOR, AUDITION_TICKS
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.shared.playback_priority import PlaybackPriority
from sampletones_application.view_model.reconstruction.waveform import (
    InstrumentWaveformViewModel,
)
from sampletones_core.audio import AudioDeviceManager
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName, GeneratorName
from sampletones_core.features.envelope import Envelope
from sampletones_core.performance.audition import audition_audio, audition_ticks
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


def _sounded(
    instrument: Optional[Instrument],
    controller: ProjectController,
    session: MagicMock,
    device: MagicMock,
    generator_name: GeneratorName,
    semitone: int,
) -> None:
    """Sounds one key of a voice on one generator, which is a choice and then a press."""
    logic = _logic(instrument, controller, session, device)
    logic.set_generator(generator_name)
    logic.sound(semitone)


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
    audio = audition_audio(
        instrument,
        channel_name,
        config,
        pitch=pitch,
        ticks=audition_ticks(instrument, cap=AUDITION_TICKS),
    )
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

        _sounded(instrument, controller, session, device, GeneratorName.PULSE, SEMITONE_G)

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

        _sounded(instrument, controller, session, device, GeneratorName.PULSE, SEMITONE_G)

        expected = _expected(instrument, controller, ChannelName.PULSE1, MIDDLE_C + 12 + SEMITONE_G)
        assert np.array_equal(_played(device), expected)

    def test_the_generator_chosen_is_the_channel_the_voice_is_heard_on(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        instrument = _instrument()

        _sounded(instrument, controller, session, device, GeneratorName.TRIANGLE, SEMITONE_G)

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
        logic.set_generator(GeneratorName.NOISE)

        logic.sound(SEMITONE_G)
        first = _played(device)
        logic.sound(0)
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
        _sounded(_instrument(), controller, session, device, GeneratorName.PULSE, SEMITONE_G)

        assert device.play.call_args.kwargs["priority"] is PlaybackPriority.PREVIEW


class TestTheCursorAnAuditionDraws:
    """A voice being sounded carries a mark along the waveform the card draws."""

    def test_an_audition_that_sounds_is_followed(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        """The device reports where it has reached, which is what moves the mark."""
        device.play.return_value = True
        logic = _logic(_instrument(), controller, session, device)
        marked: List[int] = []
        logic.on_position_changed = marked.append

        logic.sound(SEMITONE_G)
        device.set_position_callback.call_args.args[0](512)

        assert device.play.call_args.kwargs["update"] is True
        assert marked == [512]

    def test_an_audition_standing_aside_leaves_the_mark_where_it_is(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        """A preview outranked by playback the reader asked for follows nothing."""
        device.play.return_value = False
        logic = _logic(_instrument(), controller, session, device)

        logic.sound(SEMITONE_G)

        device.set_position_callback.assert_not_called()


class TestWhenNothingSounds:
    def test_a_tab_holding_no_instrument_plays_nothing(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        _sounded(None, controller, session, device, GeneratorName.PULSE, SEMITONE_G)

        device.play.assert_not_called()

    def test_a_voice_writing_no_envelope_plays_nothing(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        _sounded(Instrument(name="silent"), controller, session, device, GeneratorName.PULSE, SEMITONE_G)

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

        logic.sound(SEMITONE_G)

        assert reported == [refusal]


class TestTheWaveformTheCardDraws:
    def test_a_voice_is_first_heard_and_drawn_on_the_pulse(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        assert AUDITION_GENERATOR is GeneratorName.PULSE

        logic = _logic(_instrument(), controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn[-1] is not None
        assert drawn[-1].channel_name is ChannelName.PULSE1

    def test_the_open_voice_is_drawn_at_the_pitch_it_stands_at(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        """The card shows the voice as it is, so no key just pressed moves what it draws."""
        instrument = _instrument()
        logic = _logic(instrument, controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.sound(SEMITONE_G)
        logic.refresh()

        expected = _expected(instrument, controller, ChannelName.PULSE1, REFERENCE_PITCH)
        assert drawn[-1] is not None
        assert np.array_equal(drawn[-1].audio, expected)

    def test_choosing_a_generator_redraws_the_voice_as_that_one(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        logic = _logic(_instrument(), controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.set_generator(GeneratorName.NOISE)

        assert drawn[-1] is not None
        assert drawn[-1].channel_name is ChannelName.NOISE

    def test_the_voice_is_drawn_under_its_own_name_and_frame_length(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        instrument = _instrument()
        logic = _logic(instrument, controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        settings = controller.project.settings
        config = Config().with_library(
            nes_frequency=settings.nes_frequency,
            sample_rate=settings.sample_rate,
        )
        assert drawn[-1] is not None
        assert drawn[-1].name == "lead"
        assert drawn[-1].frame_length == config.frame_length
        sounded = audition_ticks(instrument, cap=AUDITION_TICKS)
        assert drawn[-1].audio.shape == (sounded * config.frame_length,)

    def test_a_tab_holding_a_recording_leaves_the_card_to_it(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        logic = _logic(None, controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn == [None]

    def test_a_voice_writing_no_envelope_draws_nothing(
        self,
        controller: ProjectController,
        session: MagicMock,
        device: MagicMock,
    ) -> None:
        logic = _logic(Instrument(name="silent"), controller, session, device)
        drawn: List[Optional[InstrumentWaveformViewModel]] = []
        logic.on_waveform_changed = drawn.append

        logic.refresh()

        assert drawn == [None]
