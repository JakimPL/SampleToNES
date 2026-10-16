from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Self, Tuple

from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import InstructionUnion
from sampletones_core.performance.state import ChannelPerformance
from sampletones_core.performance.ticks import sound_tick
from sampletones_core.performance.voice import VoiceReading
from sampletones_core.project.patterns.pitch import RowPitch, step_of
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels


@dataclass(frozen=True)
class LiveChannel:
    """What a live note sounds on one channel: how the channel reads the voice, and the pitch and level asked for.

    Attributes:
        reading: How the channel reads the voice.
        pitch: The pitch the key names, in the face the voice reads a key in: a note for an instrument,
            a step from the root for a sample.
        level: The level the note plays at.
    """

    reading: VoiceReading
    pitch: RowPitch
    level: int


class LiveNote:
    """One voice sounded from a key, on every channel it reads, from its strike until it runs out.

    A live note sounds what a row holding the key's pitch sounds, since it walks the song's own path: each
    channel starts the note at the step the pitch asks of the voice's reference, every tick goes through
    :func:`~sampletones_core.performance.ticks.sound_tick`, and a release silences the note as a note-off
    row does. A note runs out once every channel has: released, or past the length its voice sounds for on
    its own.

    Attributes:
        voice_id: The voice the note sounds.
    """

    def __init__(self, voice_id: str, channels: Mapping[ChannelName, LiveChannel]) -> None:
        """Strikes the note on each channel of ``channels``.

        Args:
            voice_id: The voice the note sounds.
            channels: What each channel the note sounds on reads and is asked for.
        """
        self.voice_id = voice_id
        self._readings: Dict[ChannelName, VoiceReading] = {
            channel_name: channel.reading for channel_name, channel in channels.items()
        }
        self._performances: Dict[ChannelName, ChannelPerformance] = {
            channel_name: _struck(voice_id, channel) for channel_name, channel in channels.items()
        }

    @classmethod
    def of_voice(
        cls,
        voice: VoiceUnion,
        *,
        pitches: Mapping[ChannelName, RowPitch],
        levels: Mapping[ChannelName, int],
    ) -> Self:
        """The note ``voice`` sounds on each channel it has frames on and ``pitches`` names a pitch for.

        Args:
            voice: The voice the key sounds.
            pitches: The pitch the key names on each channel.
            levels: The level the note plays at on each channel ``pitches`` names.
        """
        return cls(voice.id, live_channels(voice, pitches=pitches, levels=levels))

    @property
    def channel_names(self) -> Tuple[ChannelName, ...]:
        """The channels the note sounds on, in channel order."""
        return tuple(channel_name for channel_name in ChannelName.items() if channel_name in self._performances)

    @property
    def finished(self) -> bool:
        """Whether every channel has run out, so the note sounds nothing more."""
        return all(self._ran_out(channel_name) for channel_name in self._performances)

    def tick(self) -> Dict[ChannelName, Optional[InstructionUnion]]:
        """The instruction each channel sounds this tick, or ``None`` on a channel resting, and the step onward."""
        return {channel_name: self._tick(channel_name) for channel_name in self._performances}

    def release(self) -> None:
        """Silences the note on every channel, as a note-off row does."""
        for performance in self._performances.values():
            performance.end_note()

    def _tick(self, channel_name: ChannelName) -> Optional[InstructionUnion]:
        performance = self._performances[channel_name]
        if performance.voice_id is None:
            return None

        return sound_tick(performance, self._readings[channel_name])

    def _ran_out(self, channel_name: ChannelName) -> bool:
        performance = self._performances[channel_name]
        if performance.voice_id is None:
            return True

        length = self._readings[channel_name].length
        return length is not None and performance.tick_index >= length


def live_channels(
    voice: VoiceUnion,
    *,
    pitches: Mapping[ChannelName, RowPitch],
    levels: Mapping[ChannelName, int],
) -> Dict[ChannelName, LiveChannel]:
    """What a key asks of ``voice`` on each channel it has frames on and ``pitches`` names a pitch for.

    A note is struck from these, and a sound kept for later strikes holds them, so every strike reads the
    voice the same way.

    Args:
        voice: The voice the key sounds.
        pitches: The pitch the key names on each channel.
        levels: The level the note plays at on each channel ``pitches`` names.
    """
    channels: Dict[ChannelName, LiveChannel] = {}
    for channel_name in voice_channels(voice):
        reading = VoiceReading.read(voice, channel_name)
        if reading is not None and channel_name in pitches:
            channels[channel_name] = LiveChannel(
                reading=reading,
                pitch=pitches[channel_name],
                level=levels[channel_name],
            )

    return channels


def _struck(voice_id: str, channel: LiveChannel) -> ChannelPerformance:
    """A channel starting the note at the step the pitch asks of the voice's reference, at the level asked for."""
    performance = ChannelPerformance()
    performance.start_note(
        voice_id,
        transpose=step_of(channel.pitch, reference=channel.reading.reference),
        volume=channel.level,
    )
    return performance
