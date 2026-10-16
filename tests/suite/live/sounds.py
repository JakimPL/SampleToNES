from typing import Final

from sampletones_application.logic.shared.live import Keyboard, LiveKey, LiveSound, Strike, StrikeFollower
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features.envelope import Envelope
from sampletones_core.project.patterns.pitch import Note, Step
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.project.voices.voice import voice_channels
from tests.suite.performance import make_pulse_reconstruction

LIVE_CHANNEL: Final[ChannelName] = ChannelName.PULSE1
REFERENCE_PITCH: Final[int] = 60
SILENT_VOICE_ID: Final[str] = "unheard"


def held_instrument() -> Instrument:
    """An instrument sounding for as long as its key is down, its frames changing so a tick out of place shows."""
    return Instrument(
        name="lead",
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=(15, 13, 11), loop_point=1),
            arpeggio=Envelope[int](items=(0, 4, 7)),
            duty_cycle=Envelope[int](items=(2, 1)),
        ),
        initial_pitch=REFERENCE_PITCH,
    )


def short_sample(frames: int) -> Sample:
    """A recording of ``frames`` frames on Pulse 1, measured against :data:`REFERENCE_PITCH`."""
    return Sample(name="take", reconstruction=make_pulse_reconstruction(pitch=REFERENCE_PITCH, count=frames))


def instrument_sound(instrument: Instrument, *, note: int, config: Config) -> LiveSound:
    """What a key naming ``note`` sounds of ``instrument`` on :data:`LIVE_CHANNEL`, at full volume."""
    return LiveSound.of_voice(
        instrument,
        pitches={LIVE_CHANNEL: Note(value=note)},
        levels={LIVE_CHANNEL: MAX_VOLUME},
        config=config,
    )


def sample_sound(sample: Sample, *, step: int, config: Config) -> LiveSound:
    """What a key ``step`` keys from the root sounds of ``sample``, on every channel it plays, at full volume."""
    channels = voice_channels(sample)
    return LiveSound.of_voice(
        sample,
        pitches={channel_name: Step(value=step) for channel_name in channels},
        levels={channel_name: MAX_VOLUME for channel_name in channels},
        config=config,
    )


def unheard_sound(kind: VoiceKind) -> LiveSound:
    """A sound of a voice of ``kind`` that plays on no channel, for a case reading which press is in front."""
    return LiveSound(voice_id=SILENT_VOICE_ID, kind=kind, channels={}, config=Config())


def strike(keyboard: Keyboard, number: int, sound: LiveSound) -> Strike:
    """One press of key ``number`` on ``keyboard``, sounding ``sound``, which nothing follows."""
    return Strike(key=LiveKey(keyboard=keyboard, number=number), sound=sound, follower=None)


def followed_strike(keyboard: Keyboard, number: int, sound: LiveSound, follower: StrikeFollower) -> Strike:
    """One press of key ``number`` on ``keyboard``, sounding ``sound``, whose note ``follower`` follows."""
    return Strike(key=LiveKey(keyboard=keyboard, number=number), sound=sound, follower=follower)
