from pathlib import Path

from sampletones_core.project import Project, ProjectContainer

from .session import ProjectSession


class ProjectManager:
    """Owns the current working :class:`~sampletones_core.project.Project` and its lifecycle.

    The application always holds exactly one project.  On startup that is a
    fresh empty project; ``new`` and ``load`` replace it.  ``ProjectManager``
    does not emit callbacks — callers pull state from it directly.  For
    callback-driven mutation notifications, use :class:`ProjectController`.

    Responsibilities:
    - Create, load, save, and close the current ``Project``.
    - Maintain a :class:`~sampletones_application.logic.project.session.ProjectSession`
      that tracks whether the project has unsaved changes.
    - Delegate file I/O to ``ProjectContainer`` from ``sampletones_core``.

    Governing principles:
    - No DPG calls.  No callbacks.  No imports from ``ui/``, ``view_model/``,
      or ``coordinators/``.
    - ``mark_updated()`` is the only method that changes session dirty state
      without touching the ``Project`` object itself; it is called by
      ``ProjectController._touch()``.
    - Callers that need to react to lifecycle events should observe
      ``self.session.on_state_changed``.

    Dependencies: ``ProjectSession``, ``Project``, ``ProjectContainer``
    (from ``sampletones_core``).
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
