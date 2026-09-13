from typing import Dict, List, Mapping, Optional, Self, Sequence

from pydantic import BaseModel, ConfigDict

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.patterns.channel import Channel
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.project.voices.note_off import NoteOff
from sampletones_core.project.voices.note_on import NoteOn
from sampletones_core.project.voices.sample import Sample
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.paths import SONG_PATH


class RowSpec(BaseModel):
    """One written row of a pattern: what it plays, or that it releases the note.

    Attributes:
        row: The row's index in its pattern.
        sample: The sample the row plays, or ``None`` for a row that plays none.
        transpose: The semitones the row transposes the sample by, or ``None`` to leave it.
        volume: The volume the row sets, or ``None`` to leave it.
        off: Whether the row releases the note.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    row: int
    sample: Optional[str] = None
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


def _order(frames: Sequence[Mapping[ChannelName, int]]) -> List[Dict[ChannelName, Optional[int]]]:
    return [{channel: frame.get(channel) for channel in ChannelName.items()} for frame in frames]


def _row(spec: RowSpec, channel: ChannelName, samples_by_name: Mapping[str, Sample]) -> Row:
    if spec.off:
        return Row(command=NoteOff(), volume=spec.volume)

    if spec.sample is None:
        return Row(transpose=spec.transpose, volume=spec.volume)

    sample = samples_by_name[spec.sample]
    if channel not in sample.reconstruction.playing_channels:
        raise ValueError(f"Sample '{spec.sample}' has no '{channel.value}' slice for the {channel.value} channel")

    return Row(command=NoteOn(voice_id=sample.id), transpose=spec.transpose, volume=spec.volume)


def _pattern(
    row_specs: Sequence[RowSpec],
    rows_per_pattern: int,
    channel: ChannelName,
    samples_by_name: Mapping[str, Sample],
) -> Pattern:
    rows = [Row() for _ in range(rows_per_pattern)]
    for spec in row_specs:
        rows[spec.row] = _row(spec, channel, samples_by_name)

    return Pattern(rows=rows)


def _channels(
    channel_specs: Mapping[ChannelName, ChannelSpec],
    rows_per_pattern: int,
    samples_by_name: Mapping[str, Sample],
) -> Dict[ChannelName, Channel]:
    channels: Dict[ChannelName, Channel] = {}
    for channel, spec in channel_specs.items():
        patterns = {
            index: _pattern(row_specs, rows_per_pattern, channel, samples_by_name)
            for index, row_specs in spec.patterns.items()
        }
        channels[channel] = Channel(name=channel, patterns=patterns)

    for channel in ChannelName.items():
        channels.setdefault(channel, Channel(name=channel, patterns={}))

    return channels


def build_song(spec: SongSpec, samples_by_name: Mapping[str, Sample]) -> Song:
    """The song the spec describes, playing the named samples.

    Raises:
        KeyError: If a row names a sample the catalog lacks.
        ValueError: If a row plays a sample on a channel the sample has no slice for.
    """
    return Song(
        rows_per_pattern=spec.rows_per_pattern,
        order=_order(spec.order),
        channels=_channels(spec.channels, spec.rows_per_pattern, samples_by_name),
    )
