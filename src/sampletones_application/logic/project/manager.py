from pathlib import Path
from typing import Callable, Optional

from sampletones_core.project import Project, ProjectContainer
from sampletones_shared.logger import logger
from sampletones_shared.utils.callbacks import CallbackMixin

from .session import ProjectSession

OnPathChangedCallback = Callable[[Optional[Path]], None]


class ProjectManager(CallbackMixin):
    """
    The single authority on which project is currently open, which file it stands for, and whether it is clean.

    - Lifecycle events are emitted by its ``session``; callers that need to react to lifecycle
      transitions subscribe to ``session.on_state_changed``.
    - The project stands for the file it was last loaded from or saved to, its :attr:`path`. A
      project created here and never saved stands for none. ``on_path_changed`` reports each new
      path, so the session remembers the project the next run reopens.
    """

    def __init__(self) -> None:
        self._session: ProjectSession = ProjectSession()
        self._current: Project = Project.create()
        self._path: Optional[Path] = None

        self.on_path_changed: Optional[OnPathChangedCallback] = None

    @property
    def current(self) -> Project:
        return self._current

    @property
    def path(self) -> Optional[Path]:
        """The file the open project was last loaded from or saved to, ``None`` for a project never written."""
        return self._path

    @property
    def session(self) -> ProjectSession:
        return self._session

    @property
    def name(self) -> str:
        return self._session.name

    @property
    def is_dirty(self) -> bool:
        return self._session.unsaved_changes

    @property
    def is_open(self) -> bool:
        return self._session.is_open

    def new(self) -> None:
        self._current = Project.create()
        self._set_path(None)
        self._session.mark_loaded("")

    def close(self) -> None:
        self._current = Project.create()
        self._set_path(None)
        self._session.mark_closed()

    def load(self, path: Path) -> None:
        logger.info(f"Loading project: {logger.format_path(path)}")
        self._current = ProjectContainer.load(path)
        self._set_path(path)
        self._session.mark_loaded(path.stem)
        logger.info(f"Project {logger.format_path(path)} loaded successfully")

    def save(self, path: Path) -> None:
        ProjectContainer.save(self._current, path)
        self._set_path(path)
        self._session.mark_saved(path.stem)

    def _set_path(self, path: Optional[Path]) -> None:
        if path == self._path:
            return

        self._path = path
        self.call(self.on_path_changed, path)

    def mark_updated(self) -> None:
        self._session.mark_updated()

    def install(self, project: Project, *, clean: bool) -> None:
        """Swaps in a project restored from history, updating the session's dirty state.

        ``clean`` is true when the restored state is exactly the one last saved to
        disk; the session then reports no unsaved changes. Every other restored
        state differs from the file until the user saves again, so the session
        stays marked as having unsaved changes.
        """
        self._current = project
        if clean:
            self._session.mark_saved()
        else:
            self._session.mark_updated()
