from typing import Annotated, Dict, List, Literal, Self, Union

from pydantic import BaseModel, ConfigDict, Field

from sampletones_core.constants.enums import ChannelName
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_shared.utils.serialization import load_yaml_model
from sampletones_tools.corpus.module import ModuleConfig
from sampletones_tools.corpus.song import SongSpec
from sampletones_tools.tracker_playback.paths import CORPUS_PATH

FrameValue = Union[bool, int]


class FrameRun(BaseModel):
    """Frames one channel of a sample plays alike, one after another.

    Attributes:
        count: How many frames the run lasts.
        frame: The instruction each of those frames plays, in the fields the channel's instruction takes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    count: int = Field(..., ge=1)
    frame: Dict[str, FrameValue]


class SampleSpec(BaseModel):
    """A voice with a recording behind it, its frames written out channel by channel.

    Attributes:
        kind: Marks the voice as a sample.
        channels: The frames each channel plays, as runs of alike frames.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["sample"]
    channels: Dict[ChannelName, List[FrameRun]]


class InstrumentSpec(BaseModel):
    """An instrument: envelopes every channel reads its own way.

    Attributes:
        kind: Marks the voice as an instrument.
        initial_pitch: The note a tonal channel measures the arpeggio against.
        initial_period: The period the noise channel measures the arpeggio against.
        envelopes: The per-tick values every channel reads.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["instrument"]
    initial_pitch: int
    initial_period: int
    envelopes: InstrumentEnvelopes


VoiceSpec = Annotated[Union[SampleSpec, InstrumentSpec], Field(discriminator="kind")]


class ProjectSpec(BaseModel):
    """One project of the corpus: what it exercises, its settings, its voices and its song.

    Attributes:
        name: The name its files are written under.
        purpose: What the project exercises, in one sentence.
        module: The title, the author and the playback settings.
        voices: The corpus voices the project holds, in the order it lists them.
        song: The order and the patterns.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    purpose: str
    module: ModuleConfig
    voices: List[str]
    song: SongSpec


class ArrangementSpec(BaseModel):
    """The synthetic corpus arrangement played at one tempo.

    Attributes:
        name: The name its files are written under.
        purpose: What playing the arrangement at this tempo exercises, in one sentence.
        tempo: The tempo it is played at.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    purpose: str
    tempo: int


class CorpusSpec(BaseModel):
    """The projects a tracker playback check plays, and the voices they draw on.

    Attributes:
        voices: Every voice a project may hold, by name.
        projects: The projects written out here, each exercising one thing a song can do.
        arrangements: The synthetic corpus arrangement, reconstructed from rendered audio, at each
            tempo it is played at.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    voices: Dict[str, VoiceSpec]
    projects: List[ProjectSpec]
    arrangements: List[ArrangementSpec]

    @classmethod
    def load(cls) -> Self:
        """The corpus the package ships."""
        return load_yaml_model(CORPUS_PATH, cls)
