from pathlib import Path

from sampletones_core.project import Project, ProjectContainer

from .session import ProjectSession


class ProjectManager:
    """Owns the current working :class:`Project` and its lifecycle.

    The application always holds a project — a fresh empty one on startup, replaced
    by ``new`` or ``load``. Mirrors the reconstruction manager/session split: this
    manager holds the data plus a :class:`ProjectSession` tracking dirty state,
    while save/load I/O is delegated to :class:`ProjectContainer`.
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
        self._current = ProjectContainer.load(path)
        self._session.mark_loaded(path.stem)

    def save(self, path: Path) -> None:
        ProjectContainer.save(self._current, path)
        self._session.mark_saved(path.stem)

    def mark_updated(self) -> None:
        self._session.mark_updated()
