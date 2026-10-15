from typing import Final

from sampletones_application.config.managers.session import SessionManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.reconstruction.audition import InstrumentAuditionLogic
from sampletones_application.logic.reconstruction.keys import ArmedVoice, KeyArming
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.constants.enums import ChannelName, FeatureKey, GeneratorName
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.reconstructions import Reconstruction
from tests.suite.stems import SHARED_CHANNEL, SOLE_CHANNEL, taking_turns

from .conftest import Tab

__all__ = ["taking_turns"]

DOCUMENT_NAME: Final[str] = "turns"
DOCUMENT_VOICE: Final[str] = "turns-voice"
QUIETER: Final[Envelope[int]] = Envelope[int](items=(7,))
HELD_TICKS: Final[int] = 40


def _armed(arming: KeyArming) -> ArmedVoice:
    arming.arm()
    armed = arming.armed
    assert armed is not None
    return armed


def _opened(manager: ReconstructionManager, reconstruction: Reconstruction) -> None:
    manager.load_reconstruction_object(reconstruction, name=DOCUMENT_NAME, voice_id=DOCUMENT_VOICE)


class TestAnInstrumentArmed:
    """An instrument is armed on the channel it is auditioned on, at the project's rates, as its envelopes stand."""

    def test_an_instrument_is_armed_on_the_auditioned_channel(
        self,
        arming: KeyArming,
        audition: InstrumentAuditionLogic,
        instrument: Instrument,
    ) -> None:
        armed = _armed(arming)

        assert armed.kind is VoiceKind.INSTRUMENT
        assert set(armed.readings) == {audition.channel_name}

    def test_another_generator_arms_its_channel(
        self,
        arming: KeyArming,
        audition: InstrumentAuditionLogic,
        instrument: Instrument,
    ) -> None:
        _armed(arming)

        audition.set_generator(GeneratorName.TRIANGLE)

        assert set(_armed(arming).readings) == {ChannelName.TRIANGLE}

    def test_an_instrument_sounds_at_the_projects_rates(
        self,
        arming: KeyArming,
        controller: ProjectController,
        instrument: Instrument,
    ) -> None:
        armed = _armed(arming)

        settings = controller.project.settings
        assert armed.config.sample_rate == settings.sample_rate
        assert armed.config.library.nes_frequency == settings.nes_frequency

    def test_an_edit_arms_the_envelopes_it_wrote(
        self,
        arming: KeyArming,
        audition: InstrumentAuditionLogic,
        controller: ProjectController,
        instrument: Instrument,
    ) -> None:
        before = _armed(arming)

        controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, QUIETER)
        after = _armed(arming)

        channel_name = audition.channel_name
        assert after is not before
        assert list(after.readings[channel_name].instructions) == instrument.instructions(channel_name)
        assert list(before.readings[channel_name].instructions) != instrument.instructions(channel_name)

    def test_an_armed_voice_keeps_the_frames_it_was_armed_with_through_an_edit(
        self,
        arming: KeyArming,
        audition: InstrumentAuditionLogic,
        controller: ProjectController,
        instrument: Instrument,
    ) -> None:
        """A MIDI key may strike the armed voice while the tab edits, so the edit reaches the next arming alone.

        A held note reads past the written frames from the envelopes themselves, so those ticks are read too.
        """
        reading = _armed(arming).readings[audition.channel_name]
        frames = list(reading.instructions)
        held_on = reading.at(len(frames) + HELD_TICKS)

        controller.set_instrument_envelope(instrument.id, FeatureKey.VOLUME, QUIETER)

        assert list(reading.instructions) == frames
        assert reading.at(len(frames) + HELD_TICKS) == held_on

    def test_arming_again_with_nothing_changed_keeps_the_armed_voice(
        self,
        arming: KeyArming,
        instrument: Instrument,
    ) -> None:
        first = _armed(arming)

        second = _armed(arming)

        assert second is first

    def test_an_instrument_writing_nothing_on_its_channel_arms_nothing(
        self,
        arming: KeyArming,
        tab: Tab,
        controller: ProjectController,
    ) -> None:
        tab.instrument = controller.add_instrument(Instrument(name="silent"))

        arming.arm()

        assert arming.armed is None


class TestARecordingArmed:
    """A recording is armed as the reader hears it, at the rates it was converted at."""

    def test_a_recording_is_armed_on_every_channel_it_plays(
        self,
        arming: KeyArming,
        reconstruction_manager: ReconstructionManager,
        taking_turns: Reconstruction,
    ) -> None:
        _opened(reconstruction_manager, taking_turns)

        armed = _armed(arming)

        assert armed.kind is VoiceKind.SAMPLE
        assert set(armed.readings) == {SHARED_CHANNEL, SOLE_CHANNEL}
        assert armed.config is taking_turns.config

    def test_a_channel_switched_off_is_armed_no_more(
        self,
        arming: KeyArming,
        reconstruction_manager: ReconstructionManager,
        taking_turns: Reconstruction,
    ) -> None:
        _opened(reconstruction_manager, taking_turns)
        before = _armed(arming)

        reconstruction_manager.listening.set_channels_on(frozenset({SHARED_CHANNEL}))
        after = _armed(arming)

        assert set(before.readings) == {SHARED_CHANNEL, SOLE_CHANNEL}
        assert set(after.readings) == {SHARED_CHANNEL}

    def test_every_channel_switched_off_arms_nothing(
        self,
        arming: KeyArming,
        reconstruction_manager: ReconstructionManager,
        taking_turns: Reconstruction,
    ) -> None:
        _opened(reconstruction_manager, taking_turns)
        _armed(arming)

        reconstruction_manager.listening.set_channels_on(frozenset())
        arming.arm()

        assert arming.armed is None

    def test_an_instrument_opened_over_a_recording_is_armed_in_its_place(
        self,
        arming: KeyArming,
        reconstruction_manager: ReconstructionManager,
        taking_turns: Reconstruction,
        tab: Tab,
        instrument: Instrument,
    ) -> None:
        _opened(reconstruction_manager, taking_turns)

        assert _armed(arming).kind is VoiceKind.INSTRUMENT


class TestNothingArmed:
    def test_a_tab_showing_nothing_arms_nothing(self, arming: KeyArming) -> None:
        arming.arm()

        assert arming.armed is None

    def test_a_voice_closed_disarms_the_keys(self, arming: KeyArming, tab: Tab, instrument: Instrument) -> None:
        _armed(arming)

        tab.instrument = None
        arming.arm()

        assert arming.armed is None


class TestTheVelocitySetting:
    def test_turning_velocity_off_rearms_the_voice_with_it(
        self,
        arming: KeyArming,
        session: SessionManager,
        instrument: Instrument,
    ) -> None:
        before = _armed(arming)

        session.set_midi_settings(None, velocity_sets_volume=not before.velocity_sets_volume)

        assert _armed(arming).velocity_sets_volume is not before.velocity_sets_volume
