from sampletones_application.coordinators.export.modal import ModalWindowCoordinator
from sampletones_application.logic.export import SongExportLogic
from sampletones_application.ui.panels.dialogs.export import GUIExportWindow
from sampletones_application.view_model.shared.export import SongExportViewModel


class SongExportCoordinator(ModalWindowCoordinator[SongExportViewModel]):
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
        super().__init__(window, flow="export")
        self._logic = export_logic
        self._cancel_window = window

        self._logic.on_view_changed = self._on_view_changed
        self._logic.on_started = self._show
        self._logic.on_finished = self._take_off_screen

        self._cancel_window.on_cancel = self._logic.cancel

    @property
    def is_active(self) -> bool:
        """An export holds the screen from its first word until the outcome that ends it."""
        return self._logic.is_active

    def cleanup(self) -> None:
        """Winds a running export down for application exit."""
        self._logic.cleanup()
