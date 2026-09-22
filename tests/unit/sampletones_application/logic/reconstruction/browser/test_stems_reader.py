import os
from pathlib import Path
from typing import Final, List, Sequence, Tuple

import pytest

from sampletones_application.logic.reconstruction.browser.stems import (
    ReconstructionStemsReader,
)
from sampletones_core.constants.enums import ChannelName
from sampletones_shared.paths.extensions import EXT_FILE_RECONSTRUCTION
from tests.suite.sequencer import sample_reconstruction
from tests.suite.stems import recorded_from

RECORDINGS: Final[List[str]] = ["Lead Vocals", "Drums", "Bass"]
REWRITTEN: Final[List[str]] = ["Guitar", "Organ", "Bass"]
LATER: Final[float] = 120.0


def write_document(directory: Path, names: Sequence[str]) -> Path:
    """Writes a reconstruction recording one named audio file per name, and answers where it went."""
    reconstruction = recorded_from(
        sample_reconstruction([ChannelName.PULSE1]),
        [directory / f"{name}.wav" for name in names],
    )
    path = (directory / "song").with_suffix(EXT_FILE_RECONSTRUCTION)
    reconstruction.save(path)
    return path


def touched_later(path: Path) -> None:
    """Writes the file's clock forward, so a rewrite reads as one however fast it followed."""
    written = path.stat().st_mtime + LATER
    os.utime(path, (written, written))


class Announcements:
    def __init__(self) -> None:
        self.read: List[Tuple[Path, Tuple[str, ...]]] = []

    def __call__(self, path: Path, names: Tuple[str, ...]) -> None:
        self.read.append((path, names))


@pytest.fixture
def announcements() -> Announcements:
    return Announcements()


@pytest.fixture
def reader(announcements: Announcements) -> ReconstructionStemsReader:
    instance = ReconstructionStemsReader()
    instance.on_recordings_read = announcements
    return instance


class TestReadingADocument:
    def test_an_unread_document_answers_nothing(
        self,
        reader: ReconstructionStemsReader,
        tmp_path: Path,
    ) -> None:
        assert reader.recordings(write_document(tmp_path, RECORDINGS)) is None

    def test_the_reading_names_the_recordings_in_record_order(
        self,
        reader: ReconstructionStemsReader,
        tmp_path: Path,
    ) -> None:
        path = write_document(tmp_path, RECORDINGS)

        reader.recordings(path)

        assert reader.recordings(path) == tuple(RECORDINGS)

    def test_the_reading_is_announced_once_it_lands(
        self,
        reader: ReconstructionStemsReader,
        announcements: Announcements,
        tmp_path: Path,
    ) -> None:
        path = write_document(tmp_path, RECORDINGS)

        reader.recordings(path)

        assert announcements.read == [(path, tuple(RECORDINGS))]


class TestWhatAReadingOutlives:
    def test_a_rewritten_document_is_read_again(
        self,
        reader: ReconstructionStemsReader,
        tmp_path: Path,
    ) -> None:
        path = write_document(tmp_path, RECORDINGS)
        reader.recordings(path)

        write_document(tmp_path, REWRITTEN)
        touched_later(path)

        assert reader.recordings(path) is None
        assert reader.recordings(path) == tuple(REWRITTEN)

    def test_a_document_read_once_is_answered_without_reading_it_again(
        self,
        reader: ReconstructionStemsReader,
        announcements: Announcements,
        tmp_path: Path,
    ) -> None:
        path = write_document(tmp_path, RECORDINGS)
        reader.recordings(path)

        reader.recordings(path)

        assert len(announcements.read) == 1


class TestADocumentThatCannotBeRead:
    def test_an_unreadable_document_answers_nothing_to_show(
        self,
        reader: ReconstructionStemsReader,
        tmp_path: Path,
    ) -> None:
        path = (tmp_path / "broken").with_suffix(EXT_FILE_RECONSTRUCTION)
        path.write_bytes(b"not a document")

        reader.recordings(path)

        assert reader.recordings(path) == ()

    def test_a_document_the_disk_does_not_hold_answers_nothing_to_show(
        self,
        reader: ReconstructionStemsReader,
        tmp_path: Path,
    ) -> None:
        path = (tmp_path / "absent").with_suffix(EXT_FILE_RECONSTRUCTION)

        reader.recordings(path)

        assert reader.recordings(path) == ()
