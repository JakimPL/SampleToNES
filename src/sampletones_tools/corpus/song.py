from typing import Dict, List, Mapping, Optional, Self, Sequence

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.pitch import Step
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.voice import VoiceUnion, voice_channels
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.paths import SONG_PATH


class RowSpec(BaseModel):
    """One written row of a pattern: what it plays, or that it releases the note.

    Attributes:
        row: The row's index in its pattern.
        voice: The voice the row plays, or ``None`` for a row that plays none.
        transpose: The semitones the row transposes the voice by, or ``None`` to leave it.
        volume: The volume the row sets, or ``None`` to leave it.
        off: Whether the row releases the note.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    row: int
    voice: Optional[str] = None
    transpose: Optional[int] = None
    volume: Optional[int] = None
    off: bool = False


class ChannelSpec(BaseModel):
    """The patterns one channel holds, each as the rows written into it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    patterns: Dict[int, List[RowSpec]]


class SongSpec(BaseModel):
    """The arrangement: the pattern length, the order and the channels' patterns."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rows_per_pattern: int
    order: List[Dict[ChannelName, int]]
    channels: Dict[ChannelName, ChannelSpec]

    @classmethod
    def load(cls) -> Self:
        """The arrangement the package ships."""
        return load_yaml_model(SONG_PATH, cls)


def _order(
    frames: Sequence[Mapping[ChannelName, int]],
) -> List[Dict[ChannelName, Optional[int]]]:
    return [{channel: frame.get(channel) for channel in ChannelName.items()} for frame in frames]


def _row(spec: RowSpec, channel: ChannelName, voices_by_name: Mapping[str, VoiceUnion]) -> Row:
    if spec.off:
        return Row(command=NoteOff(), volume=spec.volume)

    pitch = Step(value=spec.transpose) if spec.transpose is not None else None
    if spec.voice is None:
        return Row(pitch=pitch, volume=spec.volume)

    voice = voices_by_name[spec.voice]
    if channel not in voice_channels(voice):
        raise ValueError(f"Voice '{spec.voice}' has no '{channel.value}' slice for the {channel.value} channel")

    return Row(
        command=NoteOn(voice_id=voice.id),
        pitch=pitch,
        volume=spec.volume,
    )


def _pattern(
    row_specs: Sequence[RowSpec],
    rows_per_pattern: int,
    channel: ChannelName,
    voices_by_name: Mapping[str, VoiceUnion],
) -> Pattern:
    rows = [Row() for _ in range(rows_per_pattern)]
    for spec in row_specs:
        rows[spec.row] = _row(spec, channel, voices_by_name)

    return Pattern(rows=tuple(rows))


def _channels(
    channel_specs: Mapping[ChannelName, ChannelSpec],
    rows_per_pattern: int,
    voices_by_name: Mapping[str, VoiceUnion],
) -> Dict[ChannelName, Channel]:
    channels: Dict[ChannelName, Channel] = {}
    for channel, spec in channel_specs.items():
        patterns = {
            index: _pattern(
                row_specs,
                rows_per_pattern,
                channel,
                voices_by_name,
            )
            for index, row_specs in spec.patterns.items()
        }
        channels[channel] = Channel(name=channel, patterns=patterns)

    for channel in ChannelName.items():
        channels.setdefault(channel, Channel(name=channel, patterns={}))

    return channels


def build_song(spec: SongSpec, voices_by_name: Mapping[str, VoiceUnion]) -> Song:
    """The song the spec describes, playing the named voices.

    Raises:
        KeyError: If a row names a voice the catalog lacks.
        ValueError: If a row plays a voice on a channel the voice has no slice for.
    """
    return Song(
        rows_per_pattern=spec.rows_per_pattern,
        order=_order(spec.order),
        channels=_channels(spec.channels, spec.rows_per_pattern, voices_by_name),
    )
