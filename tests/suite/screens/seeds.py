import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Dict, Final, List, Tuple

import numpy as np
import soundfile

from sampletones_core.compatibility.kind import ObjectKind
from sampletones_core.configs import Config, InstructionsLibraryConfig
from sampletones_core.constants.enums import ChannelName
from sampletones_core.features.envelope import Envelope
from sampletones_core.fft import Window
from sampletones_core.formats.famitracker.instrument import instrument_to_fti_bytes
from sampletones_core.formats.famitracker.model.instrument import Instrument2A03
from sampletones_core.formats.famitracker.model.sequence import InstrumentSequence
from sampletones_core.formats.famitracker.specification.instruments import STANDALONE_INSTRUMENT_INDEX
from sampletones_core.formats.famitracker.specification.sequences import SequenceKind
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.project import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_core.project.voices.envelopes import InstrumentEnvelopes
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.timing import SONG_TICK_BOUNDS, SongTiming
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, restated_document, stored_document
from tests.suite.library import build_served_library
from tests.suite.performance import place_instrument
from tests.suite.stems import recorded_from, single_entry_stems_data

FOREIGN_BYTES: Final[bytes] = b"These bytes were written by another program and belong to no SampleToNES document.\n"
TRUNCATED_FRACTION: Final[int] = 2
CONFIG_FIELD: Final[str] = "config"
RECORDING_SAMPLE_RATE: Final[int] = 44100
RECORDING_AMPLITUDE: Final[float] = 0.5
STORED_RECORDING_SECONDS: Final[float] = 0.5
STORED_RECORDING_FREQUENCY: Final[float] = 220.0
AUDIO_PATH_FIELD: Final[str] = "audio_filepath"
LINE_START_PITCH: Final[int] = 60
LINE_STEP_FRAMES: Final[int] = 15
LINE_SPAN: Final[int] = 12
LINE_VOLUME: Final[int] = 12
LINE_DUTY_CYCLE: Final[int] = 2
BASS_PITCH: Final[int] = 45
BEAT_FRAMES: Final[int] = 15
BEAT_LENGTH: Final[int] = 3
BEAT_PERIOD: Final[int] = 4
BEAT_VOLUME: Final[int] = 10
ARRANGED_FRAMES: Final[int] = 30
PAD_VOLUME: Final[Tuple[int, ...]] = (12, 8, 4)
PAD_ARPEGGIO: Final[Tuple[int, ...]] = (0, 0, 0)
FIRST_FRAME: Final[int] = 0
ONE_FRAME: Final[int] = 1
FIRST_ROW: Final[int] = 0
TURNING_PULSE_PITCH: Final[int] = 40
TURNING_PULSE_SPAN: Final[int] = 24
TURNING_SECOND_PITCH: Final[int] = 30
TURNING_SECOND_SPAN: Final[int] = 31
TURNING_TRIANGLE_PITCH: Final[int] = 30
TURNING_TRIANGLE_SPAN: Final[int] = 29
TURNING_PERIODS: Final[int] = 16
TURNING_LEVELS: Final[int] = 15
TURNING_DUTY_CYCLES: Final[int] = 4
TURNING_SECOND_LEVEL_STEP: Final[int] = 7
TURNING_NOISE_LEVEL_STEP: Final[int] = 5
TURNING_SECOND_DUTY_TICKS: Final[int] = 3
LOUDEST_LEVEL: Final[int] = 15
RELEASING_VOLUME: Final[Tuple[int, ...]] = (15, 8)
RELEASE_POINT: Final[int] = 1


class Damage(StrEnum):
    """What went wrong with a stored document before the application met it."""

    OLDER_VERSION = "older version"
    FUTURE_VERSION = "future version"
    TRUNCATED = "truncated"
    FOREIGN_BYTES = "foreign bytes"


@dataclass(frozen=True)
class CopiedFile:
    """A file laid in the home as it stands elsewhere."""

    source: Path
    destination: Path

    def write(self) -> None:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.source, self.destination)


@dataclass(frozen=True)
class WrittenBytes:
    """A file in the home holding exactly ``content``."""

    destination: Path
    content: bytes

    def write(self) -> None:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        self.destination.write_bytes(self.content)


@dataclass(frozen=True)
class Recording:
    """A recording in the home: a sine tone of ``frequency`` hertz lasting ``seconds``."""

    destination: Path
    seconds: float
    frequency: float

    def write(self) -> None:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        times = np.arange(round(self.seconds * RECORDING_SAMPLE_RATE)) / RECORDING_SAMPLE_RATE
        tone = RECORDING_AMPLITUDE * np.sin(2.0 * np.pi * self.frequency * times)
        soundfile.write(self.destination, tone, RECORDING_SAMPLE_RATE)


@dataclass(frozen=True)
class MiniLibrary:
    """A small library built for ``config``, saved where the application looks for that configuration's library.

    A conversion matches against it in seconds, and the Instructions tab browses it.
    """

    config: Config

    def write(self) -> None:
        library, key = build_served_library(self.config)
        library.save_data(key, library.data[key])


@dataclass(frozen=True)
class StoredReconstruction:
    """The reconstruction the last release wrote, laid at ``destination`` the way this build writes it.

    It names the recording :func:`stored_recording` lays in the home, so it opens with its source.
    """

    destination: Path

    def write(self) -> None:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        _stored_reconstruction().save(self.destination)


@dataclass(frozen=True)
class StoredProject:
    """A project holding the stored reconstruction as the sample ``sample`` and a hand-written ``instrument``."""

    destination: Path
    sample: str
    instrument: str

    def write(self) -> None:
        project = Project.create()
        project.voices.append(Sample(name=self.sample, reconstruction=_stored_reconstruction()))
        project.voices.append(Instrument(name=self.instrument))
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        ProjectContainer.save(project, self.destination)


@dataclass(frozen=True)
class PlayableReconstruction:
    """A reconstruction sounding a rising line on Pulse 1, a bass on the triangle and a beat on the noise.

    Each recording of ``recordings`` plays the ``frames`` frames once, in turn, so the document
    lasts as long as the recordings laid at those paths, one :class:`Recording` of ``frames`` frames
    each, and opens with its sources.
    """

    destination: Path
    recordings: Tuple[Path, ...]
    frames: int

    def write(self) -> None:
        instructions = _playable_instructions(self.frames)
        reconstruction = Reconstruction.create(
            instructions=instructions,
            config=Config(),
            coefficient=1.0,
            audio_filepath=self.recordings[:1],
            stems_data=single_entry_stems_data(list(instructions), instructions),
        )
        if len(self.recordings) > 1:
            reconstruction = recorded_from(reconstruction, self.recordings)

        self.destination.parent.mkdir(parents=True, exist_ok=True)
        reconstruction.save(self.destination)


def _playable_instructions(frames: int) -> Dict[ChannelName, List[InstructionUnion]]:
    line: List[InstructionUnion] = [
        PulseInstruction(
            on=True,
            pitch=LINE_START_PITCH + (frame // LINE_STEP_FRAMES) % LINE_SPAN,
            volume=LINE_VOLUME,
            duty_cycle=LINE_DUTY_CYCLE,
        )
        for frame in range(frames)
    ]
    bass: List[InstructionUnion] = [TriangleInstruction(on=True, pitch=BASS_PITCH) for _ in range(frames)]
    beat: List[InstructionUnion] = [
        NoiseInstruction(
            on=frame % BEAT_FRAMES < BEAT_LENGTH,
            period=BEAT_PERIOD,
            volume=BEAT_VOLUME if frame % BEAT_FRAMES < BEAT_LENGTH else 0,
            short=False,
        )
        for frame in range(frames)
    ]
    return {ChannelName.PULSE1: line, ChannelName.TRIANGLE: bass, ChannelName.NOISE: beat}


@dataclass(frozen=True)
class ArrangedProject:
    """A project with two samples and a hand-written voice, each placed once on the song's first pattern.

    ``line`` is a sample sounding Pulse 1, the triangle and the noise; ``bass`` a sample sounding the
    triangle alone; ``pad`` a hand-written voice fading on Pulse 2, its arpeggio flat. The first starts the pattern on
    Pulse 1, the hand-written voice comes in on Pulse 2 at ``pad_row``, and the bass on the triangle at
    ``bass_row``. The order plays that pattern ``order_frames`` times.
    """

    destination: Path
    line: str
    bass: str
    pad: str
    pad_row: int
    bass_row: int
    order_frames: int

    def write(self) -> None:
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
    """A project whose sample ``line`` was converted at the default tuning, and ``bass`` with A4 at ``a4_frequency`` hertz.

    The line starts the first pattern on Pulse 1 and the bass the triangle, so the song plays both.
    """

    destination: Path
    line: str
    bass: str
    a4_frequency: float

    def write(self) -> None:
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
    """A project holding two hand-written voices whose volume envelopes run long, both placed on the first pattern.

    ``long`` fades through ``long_items`` items and ``middling`` through ``middling_items``, neither
    of them ending in silence.
    """

    destination: Path
    long: str
    long_items: int
    middling: str
    middling_items: int

    def write(self) -> None:
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
    """A FamiTracker instrument file of the voice ``name``, whose volume sequence states a release point."""

    destination: Path
    name: str

    def write(self) -> None:
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
    """A hand-written voice whose volume falls from the loudest level to the quietest one before silence, over and over."""
    return Instrument(
        name=name,
        envelopes=InstrumentEnvelopes(
            volume=Envelope[int](items=tuple(LOUDEST_LEVEL - index % TURNING_LEVELS for index in range(items))),
        ),
    )


def _turning_instructions(ticks: int) -> Dict[ChannelName, List[InstructionUnion]]:
    """Every channel sounding a new pitch, level or period at each of ``ticks`` ticks."""
    return {
        ChannelName.PULSE1: [
            PulseInstruction(
                on=True,
                pitch=TURNING_PULSE_PITCH + tick % TURNING_PULSE_SPAN,
                volume=1 + tick % TURNING_LEVELS,
                duty_cycle=tick % TURNING_DUTY_CYCLES,
            )
            for tick in range(ticks)
        ],
        ChannelName.PULSE2: [
            PulseInstruction(
                on=True,
                pitch=TURNING_SECOND_PITCH + tick % TURNING_SECOND_SPAN,
                volume=1 + (tick * TURNING_SECOND_LEVEL_STEP) % TURNING_LEVELS,
                duty_cycle=(tick // TURNING_SECOND_DUTY_TICKS) % TURNING_DUTY_CYCLES,
            )
            for tick in range(ticks)
        ],
        ChannelName.TRIANGLE: [
            TriangleInstruction(on=True, pitch=TURNING_TRIANGLE_PITCH + tick % TURNING_TRIANGLE_SPAN)
            for tick in range(ticks)
        ],
        ChannelName.NOISE: [
            NoiseInstruction(
                on=True,
                period=tick % TURNING_PERIODS,
                volume=1 + (tick * TURNING_NOISE_LEVEL_STEP) % TURNING_LEVELS,
                short=bool(tick % 2),
            )
            for tick in range(ticks)
        ],
    }


def _repeat_first_frame(project: Project, order_frames: int) -> None:
    """Lays ``order_frames`` frames in the order, each playing the patterns the first one plays."""
    for _ in range(order_frames - 1):
        project.song.duplicate_frame(FIRST_FRAME)


def _save_project(project: Project, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ProjectContainer.save(project, destination)


def _detached_reconstruction(
    instructions: Dict[ChannelName, List[InstructionUnion]],
    config: Config,
) -> Reconstruction:
    """A reconstruction of ``instructions`` naming no recording, the way a project stores a sample."""
    return Reconstruction.create(
        instructions=instructions,
        config=config,
        coefficient=1.0,
        audio_filepath=(),
        stems_data=single_entry_stems_data(list(instructions), instructions),
    )


def stored_recording() -> Recording:
    """The recording the archived reconstruction names, laid where its relative path leads from the home.

    The application runs in the home, so a relative path the document names resolves there.
    """
    document = stored_document(archived(ObjectKind.RECONSTRUCTION, ARCHIVED_VERSIONS[ObjectKind.RECONSTRUCTION]))
    return Recording(
        destination=Path.cwd() / document[AUDIO_PATH_FIELD],
        seconds=STORED_RECORDING_SECONDS,
        frequency=STORED_RECORDING_FREQUENCY,
    )


def _stored_reconstruction() -> Reconstruction:
    return Reconstruction.load(archived(ObjectKind.RECONSTRUCTION, ARCHIVED_VERSIONS[ObjectKind.RECONSTRUCTION]))


def archived_document(kind: ObjectKind, destination: Path) -> CopiedFile:
    """The document of ``kind`` a release wrote, which the compatibility corpus keeps, laid at ``destination``."""
    return CopiedFile(
        source=archived(kind, ARCHIVED_VERSIONS[kind]),
        destination=destination,
    )


def archived_library(folder: Path) -> CopiedFile:
    """The library a release built, laid in ``folder`` under the name its settings give a library file."""
    source = archived(ObjectKind.LIBRARY, ARCHIVED_VERSIONS[ObjectKind.LIBRARY])
    config = Config(library=InstructionsLibraryConfig.model_validate(stored_document(source)[CONFIG_FIELD]))
    key = InstructionLibraryKey.create(config.library, Window.from_config(config))
    return CopiedFile(source=source, destination=folder / key.filename)


def damaged_document(
    kind: ObjectKind,
    damage: Damage,
    *,
    destination: Path,
    older_version: str,
    future_version: str,
) -> WrittenBytes:
    """The archived document of ``kind`` with ``damage`` done to it, laid at ``destination``.

    A document restated at ``older_version`` or ``future_version`` is whole apart from its version, so
    a refusal of it is a refusal of that version alone.
    """
    source = archived(kind, ARCHIVED_VERSIONS[kind])
    match damage:
        case Damage.OLDER_VERSION:
            content = restated_document(source, kind, older_version)
        case Damage.FUTURE_VERSION:
            content = restated_document(source, kind, future_version)
        case Damage.TRUNCATED:
            whole = source.read_bytes()
            content = whole[: len(whole) // TRUNCATED_FRACTION]
        case Damage.FOREIGN_BYTES:
            content = FOREIGN_BYTES

    return WrittenBytes(destination=destination, content=content)
