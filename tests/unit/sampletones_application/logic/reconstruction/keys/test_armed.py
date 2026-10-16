from typing import Final, List, Optional

import pytest

from sampletones_application.logic.reconstruction.keys import ArmedVoice
from sampletones_application.logic.shared.live import Keyboard, LiveKey
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_TRANSPOSE, MAX_VOLUME
from sampletones_core.performance import VoiceReading, velocity_level
from sampletones_core.project.patterns.pitch import Note, Step, played_note
from sampletones_core.project.voices.voice import VoiceUnion
from tests.suite.live import short_sample

from .conftest import REFERENCE_PERIOD, SAMPLE_ROOT, lead

KEY_CODE: Final[int] = 90
NOTE_G: Final[int] = 67
FAR_ABOVE: Final[int] = 127
SOFT: Final[int] = 20
HARD: Final[int] = 127
RECORDING_FRAMES: Final[int] = 4


def _armed(
    voice: VoiceUnion, kind: VoiceKind, channel_names: List[ChannelName], *, velocity_sets_volume: bool
) -> ArmedVoice:
    readings = {}
    for channel_name in channel_names:
        reading = VoiceReading.read(voice, channel_name)
        assert reading is not None
        readings[channel_name] = reading

    return ArmedVoice(
        voice_id=voice.id,
        kind=kind,
        readings=readings,
        config=Config(),
        sample_root=SAMPLE_ROOT,
        velocity_sets_volume=velocity_sets_volume,
    )


def _instrument_on(channel_name: ChannelName, *, velocity_sets_volume: bool) -> ArmedVoice:
    return _armed(lead(), VoiceKind.INSTRUMENT, [channel_name], velocity_sets_volume=velocity_sets_volume)


def _recording() -> ArmedVoice:
    return _armed(short_sample(RECORDING_FRAMES), VoiceKind.SAMPLE, [ChannelName.PULSE1], velocity_sets_volume=True)


def _computer() -> LiveKey:
    return LiveKey(keyboard=Keyboard.COMPUTER, number=KEY_CODE)


def _midi(note: int) -> LiveKey:
    return LiveKey(keyboard=Keyboard.MIDI, number=note)


def _ignore(_position: Optional[int]) -> None:
    return None


class TestAKeyReachesTheVoiceInItsFace:
    """An instrument hears the note a key names, or the period it states on noise; a recording hears a step from the root."""

    def test_an_instrument_sounds_at_the_note_a_key_names(self) -> None:
        strike = _instrument_on(ChannelName.PULSE1, velocity_sets_volume=True).strike(
            _computer(), NOTE_G, velocity=None, follower=_ignore
        )

        assert strike.sound.channels[ChannelName.PULSE1].pitch == Note(value=NOTE_G)

    def test_a_note_past_the_ones_played_is_held_to_the_highest(self) -> None:
        strike = _instrument_on(ChannelName.PULSE1, velocity_sets_volume=True).strike(
            _midi(FAR_ABOVE), FAR_ABOVE, velocity=HARD, follower=_ignore
        )

        assert strike.sound.channels[ChannelName.PULSE1].pitch == played_note(FAR_ABOVE)
        assert played_note(FAR_ABOVE).value < FAR_ABOVE

    def test_an_instrument_on_noise_sounds_at_the_period_it_states_whatever_the_key(self) -> None:
        armed = _instrument_on(ChannelName.NOISE, velocity_sets_volume=True)

        low = armed.strike(_computer(), SAMPLE_ROOT, velocity=None, follower=_ignore)
        high = armed.strike(_computer(), NOTE_G, velocity=None, follower=_ignore)

        assert low.sound.channels[ChannelName.NOISE].pitch == Note(value=REFERENCE_PERIOD)
        assert high.sound.channels[ChannelName.NOISE].pitch == Note(value=REFERENCE_PERIOD)

    def test_a_recording_is_stepped_from_the_root(self) -> None:
        armed = _recording()

        at_root = armed.strike(_computer(), SAMPLE_ROOT, velocity=None, follower=_ignore)
        above = armed.strike(_computer(), NOTE_G, velocity=None, follower=_ignore)

        assert at_root.sound.channels[ChannelName.PULSE1].pitch == Step(value=0)
        assert above.sound.channels[ChannelName.PULSE1].pitch == Step(value=NOTE_G - SAMPLE_ROOT)

    def test_a_step_past_the_ones_a_row_takes_is_held_to_the_widest(self) -> None:
        strike = _recording().strike(_midi(FAR_ABOVE), FAR_ABOVE + MAX_TRANSPOSE, velocity=HARD, follower=_ignore)

        assert strike.sound.channels[ChannelName.PULSE1].pitch == Step(value=MAX_TRANSPOSE)


class TestHowHardAKeyIsStruck:
    """A MIDI key's velocity sets the level where the reader chose so; a computer key and the triangle play at full level."""

    def test_a_soft_midi_key_plays_at_the_level_its_velocity_names(self) -> None:
        strike = _instrument_on(ChannelName.PULSE1, velocity_sets_volume=True).strike(
            _midi(NOTE_G), NOTE_G, velocity=SOFT, follower=_ignore
        )

        assert strike.sound.channels[ChannelName.PULSE1].level == velocity_level(ChannelName.PULSE1, SOFT)
        assert strike.sound.channels[ChannelName.PULSE1].level < MAX_VOLUME

    def test_with_velocity_off_a_soft_midi_key_plays_at_full_level(self) -> None:
        armed = _instrument_on(ChannelName.PULSE1, velocity_sets_volume=False)

        strike = armed.strike(_midi(NOTE_G), NOTE_G, velocity=SOFT, follower=_ignore)

        assert strike.sound.channels[ChannelName.PULSE1].level == MAX_VOLUME

    def test_a_computer_key_plays_at_full_level(self) -> None:
        strike = _instrument_on(ChannelName.PULSE1, velocity_sets_volume=True).strike(
            _computer(), NOTE_G, velocity=None, follower=_ignore
        )

        assert strike.sound.channels[ChannelName.PULSE1].level == MAX_VOLUME

    def test_a_soft_key_on_the_triangle_plays_at_full_level(self) -> None:
        strike = _instrument_on(ChannelName.TRIANGLE, velocity_sets_volume=True).strike(
            _midi(NOTE_G), NOTE_G, velocity=SOFT, follower=_ignore
        )

        assert strike.sound.channels[ChannelName.TRIANGLE].level == MAX_VOLUME


class TestWhatAStrikeCarries:
    def test_a_strike_carries_its_key_its_follower_and_the_voice(self) -> None:
        armed = _recording()
        heard: List[Optional[int]] = []

        strike = armed.strike(_midi(NOTE_G), NOTE_G, velocity=HARD, follower=heard.append)

        assert strike.key == _midi(NOTE_G)
        assert strike.follower == heard.append
        assert strike.sound.voice_id == armed.voice_id
        assert strike.sound.kind is VoiceKind.SAMPLE
        assert strike.sound.config is armed.config

    @pytest.mark.parametrize("kind", [VoiceKind.INSTRUMENT, VoiceKind.SAMPLE])
    def test_a_strike_sounds_on_every_channel_armed(self, kind: VoiceKind) -> None:
        armed = (
            _instrument_on(ChannelName.PULSE2, velocity_sets_volume=True)
            if kind is VoiceKind.INSTRUMENT
            else _recording()
        )

        strike = armed.strike(_computer(), NOTE_G, velocity=None, follower=_ignore)

        assert set(strike.sound.channels) == set(armed.readings)
