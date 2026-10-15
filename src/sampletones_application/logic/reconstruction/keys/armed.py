from dataclasses import dataclass
from typing import Mapping, Optional

from sampletones_application.logic.shared.live import LiveKey, LiveSound, Strike, StrikeFollower
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.constants.general import MAX_VOLUME
from sampletones_core.features import speaks_in_periods
from sampletones_core.performance import LiveChannel, VoiceReading, velocity_level
from sampletones_core.project.patterns.pitch import Note, RowPitch, clamped_step, played_note


@dataclass(frozen=True)
class ArmedVoice:
    """What a key sounds on the Reconstructions tab, ready to be struck from whichever thread a key arrives on.

    It is built on the render thread from the voice as the tab shows it and the settings a key is read under,
    and it changes nothing once built, so a MIDI key reads it whole while the tab goes on editing. A key
    reaches the voice in the face a row's pitch reaches it in: an instrument at the note the key names, or
    at the period it states on the noise channel, and a recording at the step the key stands from the root.

    Attributes:
        voice_id: The voice a key sounds.
        kind: The voice's kind, which decides the face a key reaches it in and how a release treats it.
        readings: How each channel a key sounds on reads the voice.
        config: The settings the voice is synthesized under.
        sample_root: The key playing a recording as it was recorded.
        velocity_sets_volume: Whether how hard a MIDI key is struck sets the level its note plays at.
    """

    voice_id: str
    kind: VoiceKind
    readings: Mapping[ChannelName, VoiceReading]
    config: Config
    sample_root: int
    velocity_sets_volume: bool

    def strike(
        self,
        key: LiveKey,
        pitch: int,
        *,
        velocity: Optional[int],
        follower: StrikeFollower,
    ) -> Strike:
        """One press of ``key`` naming ``pitch``, struck as hard as ``velocity`` says.

        Args:
            key: The key pressed.
            pitch: The pitch the key names, held within the notes a channel plays where it becomes one.
            velocity: How hard the key was struck, or ``None`` for a key that reports none.
            follower: What draws where the note stands.
        """
        channels = {
            channel_name: LiveChannel(
                reading=reading,
                pitch=self._pitch(channel_name, reading, pitch),
                level=self._level(channel_name, velocity),
            )
            for channel_name, reading in self.readings.items()
        }
        sound = LiveSound(voice_id=self.voice_id, kind=self.kind, channels=channels, config=self.config)
        return Strike(key=key, sound=sound, follower=follower)

    def _pitch(self, channel_name: ChannelName, reading: VoiceReading, pitch: int) -> RowPitch:
        match self.kind:
            case VoiceKind.INSTRUMENT:
                if speaks_in_periods(channel_name):
                    return Note(value=reading.reference)

                return played_note(pitch)
            case VoiceKind.SAMPLE:
                return clamped_step(pitch - self.sample_root)

    def _level(self, channel_name: ChannelName, velocity: Optional[int]) -> int:
        """The level a note plays at: full, or the one the velocity names where it sets the volume.

        The triangle's level only decides whether it sounds, so a soft strike there plays at full level.
        """
        if velocity is None or not self.velocity_sets_volume:
            return MAX_VOLUME

        level = velocity_level(channel_name, velocity)
        return MAX_VOLUME if level is None else level
