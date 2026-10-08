from datetime import datetime
from typing import Dict, Optional, Self, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from assets.demo.paths import (
    CONVERSION_PATH,
    PROJECT_PATH,
    RECORDINGS_PATH,
    VOICES_PATH,
)
from sampletones_core.constants.enums import ChannelName, HierarchyMode
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import SongSpec
from sampletones_tools.corpus.synth import SynthConfig
from sampletones_tools.synthesis.frequency import PitchSpec


class Note(BaseModel):
    """One sound in a stem: which voice strikes, when, for how long and at which pitch.

    Attributes:
        voice: The voice that sounds, by its name in the voices.
        start: When the note starts, in beats from the start of the piece.
        length: How long the note lasts, in beats, or ``None`` for the voice's own length.
        pitch: The MIDI pitch the voice's pitched oscillators sound at, or ``None`` for their own.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    voice: str
    start: float = Field(ge=0.0)
    length: Optional[float] = Field(default=None, gt=0.0)
    pitch: Optional[PitchSpec] = None


class Stem(BaseModel):
    """One recording of the piece: a named part made of notes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    notes: Tuple[Note, ...] = Field(min_length=1)


class Hit(BaseModel):
    """One recording of a single voice struck once, named as the file it becomes."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    voice: str


class Piece(BaseModel):
    """The short piece the stems play together: its name, its length and its parts.

    Attributes:
        name: The name of the folder the stems are written into, which names their mix.
        beats: The length every stem is rendered to, in beats.
        stems: The parts, in the order the mix converts them.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    beats: float = Field(gt=0.0)
    stems: Tuple[Stem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _every_note_ends_within_the_piece(self) -> Self:
        """Raises:
        ValueError: If a note starts past the end of the piece.
        """
        late = [note for stem in self.stems for note in stem.notes if note.start >= self.beats]
        if late:
            raise ValueError(f"{len(late)} notes start past the piece's {self.beats} beats")

        return self


class RecordingsSpec(BaseModel):
    """What the demo records: the hits, the piece, and the rate, tempo and level they are rendered at.

    Attributes:
        sample_rate: The sample rate of every recording.
        tempo: The beats per minute the piece's notes are placed at.
        amplitude: The peak every recording is scaled to, as a fraction of full scale.
        hits: The recordings of one voice struck once.
        piece: The piece the stems play together.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_rate: int = Field(gt=0)
    tempo: float = Field(gt=0.0)
    amplitude: float = Field(gt=0.0, le=1.0)
    hits: Tuple[Hit, ...] = Field(min_length=1)
    piece: Piece


class PieceConversion(BaseModel):
    """How the piece's stems are converted together: the channels each may take, and who picks first.

    Attributes:
        mode: Whether the levels take channels in turns or one level at a time.
        levels: The stems by name, level by level, the first level picking first.
        stems: The channels each stem may take, by the stem's name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mode: HierarchyMode
    levels: Tuple[Tuple[str, ...], ...] = Field(min_length=1)
    stems: Dict[str, Tuple[ChannelName, ...]]

    @model_validator(mode="after")
    def _every_stem_stands_on_one_level(self) -> Self:
        """Raises:
        ValueError: If a stem is missing from the levels, or named on more than one.
        """
        named = [name for level in self.levels for name in level]
        if sorted(named) != sorted(self.stems):
            raise ValueError(f"The levels name {named}, where the stems are {sorted(self.stems)}")

        return self


class ConversionSpec(BaseModel):
    """What each recording is converted with: the channels of each hit, and the setup of the piece."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    hits: Dict[str, Tuple[ChannelName, ...]]
    piece: PieceConversion


class InstrumentSpec(BaseModel):
    """An instrument of the project, as the envelopes it writes and the pitch it measures them from."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    volume: Tuple[int, ...]
    arpeggio: Tuple[int, ...]
    duty_cycle: Tuple[int, ...]
    initial_pitch: int


class ProjectSpec(BaseModel):
    """The project the demo arranges: its identity, its instruments and the song that plays them.

    Attributes:
        created: When the project reads as created and last changed, so a tree made today carries
            the dates a tree made any other day carries.
        module: The song's title, author and timing.
        instruments: The instruments the song plays, by name.
        song: The patterns and the order.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    created: datetime
    module: ModuleConfig
    instruments: Dict[str, InstrumentSpec]
    song: SongSpec


class DemoSpecification(BaseModel):
    """Everything the demo tree is made from, read from the four files the package ships.

    Each file is validated by the model that reads it, and the four are held to each other here:
    every note strikes a voice the voices declare, every recording is converted under a setup of
    its own, and every voice the song plays is a hit or an instrument.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    voices: SynthConfig
    recordings: RecordingsSpec
    conversion: ConversionSpec
    project: ProjectSpec

    @classmethod
    def load(cls) -> Self:
        """The specification the package ships."""
        return cls(
            voices=load_yaml_model(VOICES_PATH, SynthConfig),
            recordings=load_yaml_model(RECORDINGS_PATH, RecordingsSpec),
            conversion=load_yaml_model(CONVERSION_PATH, ConversionSpec),
            project=load_yaml_model(PROJECT_PATH, ProjectSpec),
        )

    @model_validator(mode="after")
    def _every_name_reaches_what_it_names(self) -> Self:
        """Raises:
        ValueError: If a note or a hit strikes a voice the voices leave out, a recording lacks a
            conversion setup, or the song plays a voice the project leaves out.
        """
        struck = {hit.voice for hit in self.recordings.hits} | {
            note.voice for stem in self.recordings.piece.stems for note in stem.notes
        }
        unknown = sorted(struck - set(self.voices.voices))
        if unknown:
            raise ValueError(f"The recordings strike voices the voices leave out: {unknown}")

        hits = [hit.name for hit in self.recordings.hits]
        if sorted(hits) != sorted(self.conversion.hits):
            raise ValueError(f"The hits are {hits}, where the conversion names {sorted(self.conversion.hits)}")

        stems = [stem.name for stem in self.recordings.piece.stems]
        if sorted(stems) != sorted(self.conversion.piece.stems):
            raise ValueError(f"The stems are {stems}, where the conversion names {sorted(self.conversion.piece.stems)}")

        played = {
            row.voice
            for channel in self.project.song.channels.values()
            for rows in channel.patterns.values()
            for row in rows
            if row.voice is not None
        }
        unknown = sorted(played - set(hits) - set(self.project.instruments))
        if unknown:
            raise ValueError(f"The song plays voices the project leaves out: {unknown}")

        return self
