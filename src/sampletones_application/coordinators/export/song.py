from typing import Optional

from sampletones_application.logic.export import SongExportLogic
from sampletones_application.ui.panels.dialogs.export import GUIExportWindow
from sampletones_application.view_model.shared.export import SongExportViewModel


class SongExportCoordinator:
    """Owns the screen a running export holds: the window opens on the run's first word and goes
    when its outcome arrives.

    An export is started from wherever the reader asked for one — a menu, a panel, the system's
    own save dialog — so nothing is orchestrated here on the way in. What is orchestrated is the
    way out: the window leaves the screen the moment the run is over, which is what lets the
    dialog reporting the outcome open onto a clear screen.
    """

    def __init__(
        self,
        export_logic: SongExportLogic,
        *,
        window: GUIExportWindow,
    ) -> None:
        self._logic = export_logic
        self._window = window
        self._view_model: Optional[SongExportViewModel] = None
        self._window_open = False

        self._logic.on_view_changed = self._on_view_changed
        self._logic.on_started = self._open
        self._logic.on_finished = self._close

        self._window.on_cancel = self._logic.cancel

    @property
    def is_active(self) -> bool:
        """An export holds the screen from its first word until the outcome that ends it."""
        return self._logic.is_active

    def cleanup(self) -> None:
        """Winds a running export down for application exit."""
        self._logic.cleanup()

    def _on_view_changed(self, view_model: SongExportViewModel) -> None:
        """Keeps the open window standing at where the run has got to."""
        self._view_model = view_model
        if self._window_open:
            self._window.update_view(view_model)

    def _open(self) -> None:
        self._window_open = True
        self._window.open(self._require_view_model())

    def _close(self) -> None:
        self._window_open = False
        self._view_model = None
        self._window.hide()

    def _require_view_model(self) -> SongExportViewModel:
        """The run the window opens on.

        Raises:
            SystemError: when the window is raised before the logic offers a view.
        """
        if self._view_model is None:
            raise SystemError("The export window is opened over the view the logic emits")

        return self._view_model
