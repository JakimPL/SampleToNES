from pathlib import Path

from sampletones_core.project import Project, ProjectContainer
from sampletones_shared.logger import logger

from .session import ProjectSession


class ProjectManager:
    """
    The single authority on which project is currently open and whether it is clean.

    - It is a passive data holder; lifecycle events are emitted by its ``session``.
    - Callers that need to react to lifecycle transitions should subscribe to
      ``session.on_state_changed``.
    """

    def __init__(self) -> None:
        self._session: ProjectSession = ProjectSession()
        self._current: Project = Project.create()

    @property
    def current(self) -> Project:
        return self._current

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
        self._session.mark_loaded("")

    def close(self) -> None:
        self._current = Project.create()
        self._session.mark_closed()

    def load(self, path: Path) -> None:
        logger.info(f"Loading project: {logger.format_path(path)}")
        self._current = ProjectContainer.load(path)
        self._session.mark_loaded(path.stem)
        logger.info(f"Project {logger.format_path(path)} loaded successfully")

    def save(self, path: Path) -> None:
        ProjectContainer.save(self._current, path)
        self._session.mark_saved(path.stem)

    def mark_updated(self) -> None:
        self._session.mark_updated()
