from pathlib import Path
from typing import Final

import pytest

from sampletones_core.constants.enums import ChannelName
from sampletones_core.formats.famitracker.builder import build_module
from sampletones_core.formats.famitracker.module import module_to_ftm_bytes
from sampletones_core.project.project import Project
from sampletones_core.project.settings import ProjectSettings
from sampletones_shared.paths.extensions import EXT_FILE_JSON, EXT_FILE_MODULE, EXT_FILE_NSF
from sampletones_shared.utils.system.system import System
from sampletones_tools.tracker_playback.targets.famitracker import target as target_module
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.markers import marked_module
from sampletones_tools.tracker_playback.targets.famitracker.program import wine
from sampletones_tools.tracker_playback.targets.famitracker.program.wine import WineProgram
from sampletones_tools.tracker_playback.targets.famitracker.target import TITLE, FamiTrackerTarget
from sampletones_tools.tracker_playback.targets.famitracker.trace import DriverTrace
from tests.suite.performance import make_pulse_reconstruction, place_instrument, project_with_sample
from tests.unit.sampletones_tools.tracker_playback.targets.famitracker.programs import StandInProgram, marking_nsf

NAME: Final[str] = "tone"
ROWS: Final[int] = 2


@pytest.fixture(name="project")
def project_fixture() -> Project:
    """A song of one frame of two rows, a note on pulse 1."""
    project, sample = project_with_sample(
        make_pulse_reconstruction(count=4),
        rows_per_pattern=ROWS,
        settings=ProjectSettings(tempo=150, speed=6, nes_frequency=60),
    )
    place_instrument(project, channel_name=ChannelName.PULSE1, row_index=0, sample=sample, volume=15)
    return project


def _program(tmp_path: Path, nsf: bytes) -> StandInProgram:
    source = tmp_path / "prepared.nsf"
    source.write_bytes(nsf)
    return StandInProgram(executable=tmp_path / "FamiTracker.exe", source=source, exported=[])


@pytest.fixture(name="documents")
def documents_fixture(tmp_path: Path) -> Path:
    path = tmp_path / "documents"
    path.mkdir()
    return path


class TestFamiTrackerTarget:
    def test_the_report_names_famitracker_and_the_program_that_exported(self, tmp_path: Path) -> None:
        target = FamiTrackerTarget(program=_program(tmp_path, marking_nsf()))

        assert target.title == TITLE
        assert str(tmp_path / "FamiTracker.exe") in target.player

    def test_the_target_runs_famitracker_the_way_this_system_does(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        executable = tmp_path / "FamiTracker.exe"
        executable.write_bytes(b"MZ")
        monkeypatch.setattr(System, "current", classmethod(lambda cls: System.LINUX))
        monkeypatch.setattr(wine, "locate_program", lambda program: Path("/usr/bin") / program)

        assert FamiTrackerTarget.located(executable).program == WineProgram(
            wine=Path("/usr/bin/wine"),
            executable=executable,
        )


class TestPlayingAProject:
    def test_the_module_is_kept_as_the_export_built_it(
        self,
        tmp_path: Path,
        documents: Path,
        project: Project,
    ) -> None:
        playback = FamiTrackerTarget(program=_program(tmp_path, marking_nsf())).play(project, documents, NAME)

        assert playback.document == documents / f"{NAME}{EXT_FILE_MODULE}"
        assert playback.document.read_bytes() == module_to_ftm_bytes(build_module(project).document)

    def test_famitracker_exports_the_module_with_its_rows_marked(
        self,
        tmp_path: Path,
        documents: Path,
        project: Project,
    ) -> None:
        program = _program(tmp_path, marking_nsf())

        FamiTrackerTarget(program=program).play(project, documents, NAME)

        assert program.exported == [module_to_ftm_bytes(marked_module(build_module(project).document))]

    def test_the_nsf_and_every_write_its_driver_made_are_kept_beside_the_module(
        self,
        tmp_path: Path,
        documents: Path,
        project: Project,
    ) -> None:
        playback = FamiTrackerTarget(program=_program(tmp_path, marking_nsf())).play(project, documents, NAME)

        recorded = DriverTrace.model_validate_json((documents / f"{NAME}{EXT_FILE_JSON}").read_text(encoding="utf-8"))
        assert (documents / f"{NAME}{EXT_FILE_NSF}").read_bytes() == marking_nsf()
        assert len(recorded.ticks) == playback.trace.ticks == ROWS

    def test_an_nsf_that_fails_to_play_is_reported(
        self,
        tmp_path: Path,
        documents: Path,
        project: Project,
    ) -> None:
        target = FamiTrackerTarget(program=_program(tmp_path, b"not an NSF file at all"))

        with pytest.raises(FamiTrackerError, match="failed to play"):
            target.play(project, documents, NAME)

    def test_a_project_a_module_has_no_room_for_is_reported(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        documents: Path,
        project: Project,
    ) -> None:
        def build_module(refused: Project) -> None:
            raise ValueError("Order length 129 exceeds the FamiTracker limit of 128 frames")

        monkeypatch.setattr(target_module, "build_module", build_module)

        with pytest.raises(FamiTrackerError, match="129"):
            FamiTrackerTarget(program=_program(tmp_path, marking_nsf())).play(project, documents, NAME)
