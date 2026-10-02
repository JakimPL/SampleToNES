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
from sampletones_core.fft import Window
from sampletones_core.instructions import InstructionUnion, NoiseInstruction, PulseInstruction, TriangleInstruction
from sampletones_core.library.key import InstructionLibraryKey
from sampletones_core.project import ProjectContainer
from sampletones_core.project.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, restated_document, stored_document
from tests.suite.library import build_served_library
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
