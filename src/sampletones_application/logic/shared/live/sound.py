from dataclasses import dataclass
from typing import Mapping, Self

from sampletones_application.view_model.sequencer.kind import voice_kind
from sampletones_application.view_model.sequencer.voices import VoiceKind
from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.performance import LiveChannel, LiveNote, live_channels
from sampletones_core.project.patterns.pitch import RowPitch
from sampletones_core.project.voices.voice import VoiceUnion


@dataclass(frozen=True)
class LiveSound:
    """What one press of a key sounds: a voice on each channel it reads, and the settings it is synthesized under.

    A sound is fixed at the press, so a key returned to strikes what it struck when it went down. The thread
    writing to the device reads it for as long as its note plays, an instrument's envelopes included, so it is
    built from a copy of the voice that edits leave as it is, and an edit reaches the next press.

    Attributes:
        voice_id: The voice the key sounds.
        kind: The voice's kind, which decides how a release treats it.
        channels: What each channel the voice sounds on reads and is asked for.
        config: The settings the voice is synthesized under, its tick rate and tuning among them.
    """

    voice_id: str
    kind: VoiceKind
    channels: Mapping[ChannelName, LiveChannel]
    config: Config

    @classmethod
    def of_voice(
        cls,
        voice: VoiceUnion,
        *,
        pitches: Mapping[ChannelName, RowPitch],
        levels: Mapping[ChannelName, int],
        config: Config,
    ) -> Self:
        """What a key sounds of ``voice`` at the pitch and level it asks on each channel.

        Args:
            voice: A copy of the voice the key sounds, taken for the press or before it.
            pitches: The pitch the key names on each channel.
            levels: The level the note plays at on each channel ``pitches`` names.
            config: The settings the voice is synthesized under.
        """
        return cls(
            voice_id=voice.id,
            kind=voice_kind(voice),
            channels=live_channels(voice, pitches=pitches, levels=levels),
            config=config,
        )

    def note(self) -> LiveNote:
        """A note of this sound struck afresh, from its first tick."""
        return LiveNote(self.voice_id, self.channels)
