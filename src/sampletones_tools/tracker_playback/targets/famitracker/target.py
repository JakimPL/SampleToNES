from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, Self

from sampletones_core.exporters.skipped import BuiltDocument
from sampletones_core.formats.famitracker.builder import build_module
from sampletones_core.formats.famitracker.model.module import FamiTrackerModule
from sampletones_core.formats.famitracker.module import module_to_ftm_bytes
from sampletones_core.project.project import Project
from sampletones_shared.exceptions.validation import InvalidDataError
from sampletones_shared.paths.extensions import EXT_FILE_JSON, EXT_FILE_LOG, EXT_FILE_MODULE, EXT_FILE_NSF
from sampletones_tools.console.errors import ConsoleError
from sampletones_tools.console.machine import Console
from sampletones_tools.tracker_playback.targets.famitracker.errors import FamiTrackerError
from sampletones_tools.tracker_playback.targets.famitracker.export import export_nsf
from sampletones_tools.tracker_playback.targets.famitracker.markers import marked_module
from sampletones_tools.tracker_playback.targets.famitracker.program.factory import located_program
from sampletones_tools.tracker_playback.targets.famitracker.program.protocol import FamiTrackerProgram
from sampletones_tools.tracker_playback.targets.famitracker.trace import DriverTrace, recorded_trace
from sampletones_tools.tracker_playback.targets.protocol import TargetPlayback

TITLE: Final[str] = "FamiTracker"
PLAYER: Final[str] = "FamiTracker's own sound driver, in the NSF `{executable}` exported, run on an emulated 6502"


@dataclass(frozen=True)
class FamiTrackerTarget:
    """FamiTracker as a playback target: a project exported to a module, which FamiTracker exports to an NSF.

    The NSF carries FamiTracker's own sound driver, the code a console or an NSF player runs, so
    running it on an emulated 6502 plays the module the way FamiTracker's exports play it.

    Attributes:
        program: FamiTracker, as this system runs it.
    """

    program: FamiTrackerProgram

    @classmethod
    def located(cls, executable: Path) -> Self:
        """The target exporting with FamiTracker at ``executable``.

        Args:
            executable: The FamiTracker program file.

        Returns:
            Self: The target.

        Raises:
            FamiTrackerError: If ``executable`` is no Windows program file, or Wine is absent where it is needed.
        """
        return cls(program=located_program(executable))

    @property
    def title(self) -> str:
        """The tracker's name, as the report prints it."""
        return TITLE

    @property
    def player(self) -> str:
        """The program whose NSF driver plays the modules, as the report introduces it."""
        return PLAYER.format(executable=self.program.executable)

    def play(
        self,
        project: Project,
        directory: Path,
        name: str,
    ) -> TargetPlayback:
        """Exports a project to a module, has FamiTracker export it to an NSF, and reads every tick its driver plays.

        The module is built by the exporter the application's FamiTracker export runs and kept as
        it is. FamiTracker exports a copy with a marker on every row (see :func:`marked_module`),
        so its NSF says where each row starts. The NSF and every write its driver made are kept
        beside the module.

        Args:
            project: The project to export and play.
            directory: Where the module, the NSF and the driver's writes are written.
            name: The stem every file is written under.

        Returns:
            TargetPlayback: The module, what FamiTracker played of it, and what the export left out.

        Raises:
            FamiTrackerError: If the project exceeds what a module holds, FamiTracker writes no NSF,
                or its NSF fails to play.
        """
        built = _built_module(project, name)
        document = directory / f"{name}{EXT_FILE_MODULE}"
        document.write_bytes(module_to_ftm_bytes(built.document))
        nsf = directory / f"{name}{EXT_FILE_NSF}"
        self._export_marked(built.document, nsf, name)
        recorded = _played(nsf, built.document)
        (directory / f"{name}{EXT_FILE_JSON}").write_text(recorded.model_dump_json(), encoding="utf-8")
        return TargetPlayback(
            document=document,
            trace=recorded.song_trace(),
            skipped_rows=len(built.skipped_rows),
            truncation=built.truncation,
        )

    def _export_marked(
        self,
        module: FamiTrackerModule,
        nsf: Path,
        name: str,
    ) -> None:
        with TemporaryDirectory() as scratch:
            marked = Path(scratch) / f"{name}{EXT_FILE_MODULE}"
            marked.write_bytes(module_to_ftm_bytes(marked_module(module)))
            export_nsf(self.program, marked, nsf, Path(scratch) / f"{name}{EXT_FILE_LOG}")


def _built_module(project: Project, name: str) -> BuiltDocument[FamiTrackerModule]:
    try:
        return build_module(project)
    except ValueError as error:
        raise FamiTrackerError(f"{name} doesn't fit a FamiTracker module: {error}") from error


def _played(nsf: Path, module: FamiTrackerModule) -> DriverTrace:
    try:
        return recorded_trace(
            Console(nsf.read_bytes()),
            frames=len(module.track.order),
            rows=module.track.rows_per_pattern,
        )
    except (ConsoleError, InvalidDataError) as error:
        raise FamiTrackerError(f"The NSF FamiTracker exported to {nsf} failed to play: {error}") from error
