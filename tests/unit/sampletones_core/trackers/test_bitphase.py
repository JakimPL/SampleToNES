import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Final, List, Optional

import numpy as np
import pytest

from sampletones_core.constants.enums import GeneratorName
from sampletones_core.exporters import Features
from sampletones_core.paths import EXT_FILE_BITPHASE, EXT_FILE_JSON
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_core.trackers.format import TrackerFormat
from sampletones_core.trackers.implementation.bitphase import (
    BitphaseBackend,
    BitphasePresetBackend,
)
from sampletones_core.trackers.request import (
    InstrumentExport,
    ProjectExport,
    SampleExport,
)
from sampletones_core.trackers.scope import ExportScope

NES_FREQUENCY: Final[int] = 60
REFERENCE_PITCH: Final[int] = 60
ENVELOPE_FRAMES: Final[int] = 16
LONG_ENVELOPE_FRAMES: Final[int] = 600
PROJECT_TITLE: Final[str] = "Demo"


PRESET_SCOPES: List[ExportScope] = [ExportScope.INSTRUMENT, ExportScope.SAMPLE]


def build_features(frames: int, *, duty_cycle_frames: Optional[int] = None) -> Features:
    duty_cycle = None if duty_cycle_frames is None else np.zeros(duty_cycle_frames, dtype=int)
    return Features(
        initial_pitch=REFERENCE_PITCH,
        volume=np.full(frames, 15, dtype=int),
        arpeggio=np.zeros(frames, dtype=int),
        pitch=None,
        hi_pitch=None,
        duty_cycle=duty_cycle,
    )


def build_instrument(name: str, frames: int) -> InstrumentExport:
    return InstrumentExport(
        name=name,
        generator=GeneratorName.PULSE1,
        features=build_features(frames),
        loop=False,
        nes_frequency=NES_FREQUENCY,
    )


def build_sample(name: str, *instruments: InstrumentExport) -> SampleExport:
    return SampleExport(name=name, instruments=instruments, nes_frequency=NES_FREQUENCY)


def read_document(destination: Path) -> Dict[str, Any]:
    document: Dict[str, Any] = json.loads(gzip.decompress(destination.read_bytes()))
    return document


@pytest.fixture(name="backend")
def backend_fixture() -> BitphaseBackend:
    return BitphaseBackend()


@pytest.fixture(name="preset_backend")
def preset_backend_fixture() -> BitphasePresetBackend:
    return BitphasePresetBackend()


@pytest.fixture(name="project")
def project_fixture() -> Project:
    return Project.create(title=PROJECT_TITLE, author="Tester", settings=ProjectSettings())


class TestFormatDeclaration:
    def test_the_backend_names_its_format(self, backend: BitphaseBackend) -> None:
        assert backend.tracker_format == TrackerFormat.BITPHASE

    def test_every_scope_is_supported(self, backend: BitphaseBackend) -> None:
        assert backend.supported_scopes == frozenset(ExportScope)

    @pytest.mark.parametrize("scope", list(ExportScope))
    def test_every_scope_carries_the_document_extension(self, backend: BitphaseBackend, scope: ExportScope) -> None:
        assert backend.extension(scope) == EXT_FILE_BITPHASE


class TestWriteInstrument:
    def test_the_file_is_written_and_reported(self, backend: BitphaseBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Short{EXT_FILE_BITPHASE}"

        artifact = backend.write_instrument(destination, build_instrument("Short", ENVELOPE_FRAMES))

        assert destination.exists()
        assert artifact.paths == (destination,)

    def test_the_document_holds_the_slice(self, backend: BitphaseBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Short{EXT_FILE_BITPHASE}"
        backend.write_instrument(destination, build_instrument("Short", ENVELOPE_FRAMES))

        document = read_document(destination)

        assert [instrument["name"] for instrument in document["instruments"]] == ["Short"]

    def test_a_long_envelope_crosses_over_whole(self, backend: BitphaseBackend, tmp_path: Path) -> None:
        """Bitphase stores instrument rows without a length limit, so a reconstruction
        reaches the document at its full length.
        """
        destination = tmp_path / f"Long{EXT_FILE_BITPHASE}"
        artifact = backend.write_instrument(destination, build_instrument("Long", LONG_ENVELOPE_FRAMES))

        document = read_document(destination)

        assert len(document["instruments"][0]["rows"]) == LONG_ENVELOPE_FRAMES
        assert artifact.truncation is None


class TestWriteSample:
    def test_every_slice_lands_in_one_document(self, backend: BitphaseBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Kick{EXT_FILE_BITPHASE}"
        request = build_sample(
            "Kick",
            build_instrument("Kick (pulse1)", ENVELOPE_FRAMES),
            build_instrument("Kick (noise)", ENVELOPE_FRAMES),
        )

        artifact = backend.write_sample(destination, request)

        assert artifact.paths == (destination,)
        assert len(read_document(destination)["instruments"]) == 2

    def test_the_document_is_named_after_the_reconstruction(self, backend: BitphaseBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Kick{EXT_FILE_BITPHASE}"
        backend.write_sample(destination, build_sample("Kick", build_instrument("Kick", ENVELOPE_FRAMES)))

        assert read_document(destination)["name"] == "Kick"


class TestWriteProject:
    def test_the_document_is_written_and_reported(
        self,
        backend: BitphaseBackend,
        project: Project,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / f"Demo{EXT_FILE_BITPHASE}"

        artifact = backend.write_project(destination, ProjectExport(project=project))

        assert artifact.paths == (destination,)
        assert destination.exists()

    def test_the_document_takes_the_project_title(
        self,
        backend: BitphaseBackend,
        project: Project,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / f"Demo{EXT_FILE_BITPHASE}"
        backend.write_project(destination, ProjectExport(project=project))

        assert read_document(destination)["name"] == PROJECT_TITLE


class TestThePresetBackend:
    def test_the_backend_names_its_format(self, preset_backend: BitphasePresetBackend) -> None:
        assert preset_backend.tracker_format == TrackerFormat.BITPHASE_PRESET

    def test_a_preset_holds_instruments_rather_than_a_song(self, preset_backend: BitphasePresetBackend) -> None:
        assert preset_backend.supported_scopes == frozenset({ExportScope.INSTRUMENT, ExportScope.SAMPLE})

    @pytest.mark.parametrize("scope", PRESET_SCOPES, ids=lambda scope: str(scope))
    def test_every_supported_scope_carries_the_preset_extension(
        self,
        preset_backend: BitphasePresetBackend,
        scope: ExportScope,
    ) -> None:
        assert preset_backend.extension(scope) == EXT_FILE_JSON

    def test_one_slice_lands_in_a_file(self, preset_backend: BitphasePresetBackend, tmp_path: Path) -> None:
        destination = tmp_path / f"Lead{EXT_FILE_JSON}"

        artifact = preset_backend.write_instrument(destination, build_instrument("Lead", ENVELOPE_FRAMES))

        assert artifact.paths == (destination,)
        assert json.loads(destination.read_text(encoding="utf-8"))["name"] == "Lead"

    def test_each_slice_lands_beside_the_destination_named_after_its_instrument(
        self,
        preset_backend: BitphasePresetBackend,
        tmp_path: Path,
    ) -> None:
        destination = tmp_path / f"Kick{EXT_FILE_JSON}"
        request = build_sample(
            "Kick",
            build_instrument("Kick (pulse1)", ENVELOPE_FRAMES),
            build_instrument("Kick (noise)", ENVELOPE_FRAMES),
        )

        artifact = preset_backend.write_sample(destination, request)

        assert artifact.paths == (
            tmp_path / f"Kick (pulse1){EXT_FILE_JSON}",
            tmp_path / f"Kick (noise){EXT_FILE_JSON}",
        )
        assert all(path.exists() for path in artifact.paths)

    def test_a_missing_directory_is_created(self, preset_backend: BitphasePresetBackend, tmp_path: Path) -> None:
        destination = tmp_path / "nested" / f"Kick{EXT_FILE_JSON}"

        preset_backend.write_sample(destination, build_sample("Kick", build_instrument("Kick", ENVELOPE_FRAMES)))

        assert destination.parent.is_dir()

    def test_a_project_is_refused(
        self,
        preset_backend: BitphasePresetBackend,
        project: Project,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(ValueError, match="one instrument"):
            preset_backend.write_project(tmp_path / f"Demo{EXT_FILE_JSON}", ProjectExport(project=project))
