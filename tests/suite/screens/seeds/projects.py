from dataclasses import dataclass
from pathlib import Path
from typing import Final, Tuple

from sampletones_core.configs import Config
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.formats.famitracker.instrument import instrument_to_fti_bytes
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.instruments import STANDALONE_INSTRUMENT_INDEX
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind
from sampletones_core.project import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from tests.suite.history.projects import every_part_project
from tests.suite.performance import place_instrument
from tests.suite.screens.seeds.constants import TURNING_LEVELS
from tests.suite.screens.seeds.reconstructions import (
    _detached_reconstruction,
    _playable_instructions,
    _stored_reconstruction,
    _turning_instructions,
)

ARRANGED_FRAMES: Final[int] = 30
PAD_VOLUME: Final[Tuple[int, ...]] = (12, 8, 4)
PAD_ARPEGGIO: Final[Tuple[int, ...]] = (0, 0, 0)
FIRST_FRAME: Final[int] = 0
ONE_FRAME: Final[int] = 1
FIRST_ROW: Final[int] = 0
LOUDEST_LEVEL: Final[int] = 15
RELEASING_VOLUME: Final[Tuple[int, ...]] = (15, 8)
RELEASE_POINT: Final[int] = 1


@dataclass(frozen=True)
class StoredProject:
    """A project holding the stored reconstruction as the sample ``sample`` and a hand-written
    ``instrument``.
    """

    destination: Path
    sample: str
    instrument: str

    def write(self) -> None:
        """Saves the project to the destination."""
        project = Project.create()
        project.voices.append(Sample(name=self.sample, reconstruction=_stored_reconstruction()))
        project.voices.append(Instrument(name=self.instrument))
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        ProjectContainer.save(project, self.destination)


@dataclass(frozen=True)
class EveryPartProject:
    """The project holding something in every part a history gesture reaches, as the history tiers below build it."""

    destination: Path

    def write(self) -> None:
        """Saves the project to the destination."""
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        ProjectContainer.save(every_part_project(), self.destination)


@dataclass(frozen=True)
class ArrangedProject:
    """A project with two samples and a hand-written voice, each placed once on the song's first pattern.

    ``line`` is a sample sounding Pulse 1, the triangle and the noise; ``bass`` a sample sounding the
    triangle alone; ``pad`` a hand-written voice fading on Pulse 2, its arpeggio flat. The line starts
    the pattern on Pulse 1, the hand-written voice comes in on Pulse 2 at ``pad_row``, and the bass on
    the triangle at ``bass_row``. The order plays that pattern ``order_frames`` times.
    """

    destination: Path
    line: str
    bass: str
    pad: str
    pad_row: int
    bass_row: int
    order_frames: int

    def write(self) -> None:
        """Saves the project to the destination."""
        line_instructions = _playable_instructions(ARRANGED_FRAMES)
        bass_instructions = {ChannelName.TRIANGLE: line_instructions[ChannelName.TRIANGLE]}
        project = Project.create()
        line = Sample(name=self.line, reconstruction=_detached_reconstruction(line_instructions, Config()))
        bass = Sample(name=self.bass, reconstruction=_detached_reconstruction(bass_instructions, Config()))
        pad = Instrument(
            name=self.pad,
            envelopes=InstrumentEnvelopes(
                volume=Envelope[int](items=PAD_VOLUME),
                arpeggio=Envelope[int](items=PAD_ARPEGGIO),
            ),
        )
        for voice in (line, bass, pad):
            project.voices.append(voice)

        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=line)
        place_instrument(project, channel_name=ChannelName.PULSE2, row_index=self.pad_row, sample=pad)
        place_instrument(project, channel_name=ChannelName.TRIANGLE, row_index=self.bass_row, sample=bass)
        _repeat_first_frame(project, self.order_frames)
        _save_project(project, self.destination)


@dataclass(frozen=True)
class OverlongProject:
    """A project whose song changes on every channel at every tick, through ``order_frames`` frames.

    Its one sample, ``sample``, plays a new value on each channel at every tick for as long as a
    frame lasts, and every frame of the order plays it from the top. Stored tick by tick, the song
    outgrows the room an NSF program has; stored with each repeat saved once, it fits.
    """

    destination: Path
    sample: str
    order_frames: int

    def write(self) -> None:
        """Saves the project to the destination."""
        project = Project.create()
        ticks = SongTiming.from_project(project, bounds=SONG_TICK_BOUNDS).frame_tick(ONE_FRAME)
        sample = Sample(
            name=self.sample, reconstruction=_detached_reconstruction(_turning_instructions(ticks), Config())
        )
        project.voices.append(sample)
        for channel in ChannelName.items():
            place_instrument(project, channel_name=channel, row_index=FIRST_ROW, sample=sample)

        _repeat_first_frame(project, self.order_frames)
        _save_project(project, self.destination)


@dataclass(frozen=True)
class TwoTuningsProject:
    """A project whose sample ``line`` was converted at the default tuning, and ``bass`` with A4 at
    ``a4_frequency`` hertz.

    The line starts the first pattern on Pulse 1 and the bass the triangle, so the song plays both.
    """

    destination: Path
    line: str
    bass: str
    a4_frequency: float

    def write(self) -> None:
        """Saves the project to the destination."""
        line_instructions = _playable_instructions(ARRANGED_FRAMES)
        bass_instructions = {ChannelName.TRIANGLE: line_instructions[ChannelName.TRIANGLE]}
        default = Config()
        retuned = default.model_copy(
            update={"library": default.library.model_copy(update={"a4_frequency": self.a4_frequency})}
        )
        project = Project.create()
        line = Sample(name=self.line, reconstruction=_detached_reconstruction(line_instructions, default))
        bass = Sample(name=self.bass, reconstruction=_detached_reconstruction(bass_instructions, retuned))
        for voice in (line, bass):
            project.voices.append(voice)

        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=FIRST_ROW, sample=line)
        place_instrument(project, channel_name=ChannelName.TRIANGLE, row_index=FIRST_ROW, sample=bass)
        _save_project(project, self.destination)


@dataclass(frozen=True)
class LongEnvelopeProject:
    """A project holding two hand-written voices whose volume envelopes run long, both placed on the first
    pattern.

    ``long`` fades through ``long_items`` items and ``middling`` through ``middling_items``, neither
    of them ending in silence.
    """

    destination: Path
    long: str
    long_items: int
    middling: str
    middling_items: int

    def write(self) -> None:
        """Saves the project to the destination."""
        project = Project.create()
        long = _fading_instrument(self.long, self.long_items)
        middling = _fading_instrument(self.middling, self.middling_items)
        for voice in (long, middling):
            project.voices.append(voice)

        place_instrument(project, channel_name=ChannelName.PULSE1, row_index=FIRST_ROW, sample=long)
        place_instrument(project, channel_name=ChannelName.PULSE2, row_index=FIRST_ROW, sample=middling)
        _save_project(project, self.destination)


@dataclass(frozen=True)
class ReleasingInstrumentFile:
    """A FamiTracker instrument file of the voice ``name``, whose volume sequence has a release point."""

    destination: Path
    name: str

    def write(self) -> None:
        """Writes the instrument file to the destination."""
        sequences = {kind: InstrumentSequence(kind=kind) for kind in SequenceKind}
        sequences[SequenceKind.VOLUME] = InstrumentSequence(
            kind=SequenceKind.VOLUME,
            items=RELEASING_VOLUME,
            release_point=RELEASE_POINT,
        )
        instrument = Instrument2A03(index=STANDALONE_INSTRUMENT_INDEX, name=self.name, sequences=sequences)
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.destination.write_bytes(instrument_to_fti_bytes(instrument))


def _fading_instrument(name: str, items: int) -> Instrument:
    """A hand-written voice whose volume falls from the loudest level through the quieter ones, over and
    over.
    """
    return Instrument(
        name=name,
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=tuple(LOUDEST_LEVEL - index % TURNING_LEVELS for index in range(items))),
        ),
    )


def _repeat_first_frame(project: Project, order_frames: int) -> None:
    """Lays ``order_frames`` frames in the order, each playing the patterns the first one plays."""
    for _ in range(order_frames - 1):
        project.song.duplicate_frame(FIRST_FRAME)


def _save_project(project: Project, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ProjectContainer.save(project, destination)
