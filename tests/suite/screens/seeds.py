import shutil
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import numpy as np
import soundfile

from sampletones_core.compatibility.kind import ObjectKind
from tests.suite.compatibility import ARCHIVED_VERSIONS, archived, restated_document

FOREIGN_BYTES: Final[bytes] = b"These bytes were written by another program and belong to no SampleToNES document.\n"
TRUNCATED_FRACTION: Final[int] = 2
RECORDING_SAMPLE_RATE: Final[int] = 44100
RECORDING_AMPLITUDE: Final[float] = 0.5


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


def archived_document(kind: ObjectKind, destination: Path) -> CopiedFile:
    """The document of ``kind`` a release wrote, which the compatibility corpus keeps, laid at ``destination``."""
    return CopiedFile(
        source=archived(kind, ARCHIVED_VERSIONS[kind]),
        destination=destination,
    )


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
