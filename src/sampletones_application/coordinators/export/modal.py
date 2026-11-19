from typing import Generic, Optional, Protocol, TypeVar

ViewModelT = TypeVar("ViewModelT")
ViewModelT_contra = TypeVar("ViewModelT_contra", contravariant=True)


class ModalWindowProtocol(Protocol[ViewModelT_contra]):
    """The window a modal flow shows, opened on a view and kept standing at each later one."""

    def open(self, view_model: ViewModelT_contra) -> None: ...

    def update_view(self, view_model: ViewModelT_contra) -> None: ...

    def hide(self) -> None: ...


class ModalWindowCoordinator(Generic[ViewModelT]):
    """The window of one modal flow, standing at the view its logic emitted last.

    A render, a program export's setup and a running export each open their window on the view
    their logic has emitted, follow each view after it while the window stands, and forget it once
    the window leaves the screen, so a window opens on the flow as it stands now.
    """

    def __init__(self, window: ModalWindowProtocol[ViewModelT], *, flow: str) -> None:
        self._window = window
        self._flow = flow
        self._view_model: Optional[ViewModelT] = None
        self._window_open = False

    def _on_view_changed(self, view_model: ViewModelT) -> None:
        """Keeps the open window standing at where the flow has got to."""
        self._view_model = view_model
        if self._window_open:
            self._window.update_view(view_model)

    def _show(self) -> None:
        """Opens the window on the view the logic emitted last."""
        self._window_open = True
        self._window.open(self._require_view_model())

    def _take_off_screen(self) -> None:
        self._window_open = False
        self._view_model = None
        self._window.hide()

    def _require_view_model(self) -> ViewModelT:
        """The view the window opens on.

        Raises:
            SystemError: When the window is raised before the logic offers a view.
        """
        if self._view_model is None:
            raise SystemError(f"The {self._flow} window is opened over the view the logic emits")

        return self._view_model
