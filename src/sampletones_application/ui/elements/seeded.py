from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar

from sampletones_application.layout.primitives import DialogGeometry
from sampletones_application.ui.elements.dialog import GUIDialogWindow
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource

ViewModel = TypeVar("ViewModel")


class GUISeededDialogWindow(GUIDialogWindow, ABC, Generic[ViewModel]):
    """A dialog drawn from one view model, re-seeded for as long as it stands.

    What a settings form or a running job shows is settled before its tree is built, so seeding
    and drawing are one act with a rebuild in between: :meth:`open` seeds the window and raises
    it, :meth:`update_view` seeds it again and re-draws the controls in place, and the rebuild
    itself has nothing left to capture. A window drawn before it was seeded reports that rather
    than showing a form of empty fields.
    """

    def __init__(
        self,
        tag: str,
        geometry: DialogGeometry,
        *,
        subject: str,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._subject = subject
        self._view_model: Optional[ViewModel] = None

        super().__init__(
            tag,
            geometry,
            key_router=key_router,
            shortcut_source=shortcut_source,
        )

    def open(self, view_model: ViewModel) -> None:
        """Shows the window seeded with what it is to draw."""
        self._view_model = view_model
        self.show()

    def prepare(self, *_args: Any, **_kwargs: Any) -> None:
        """The values drawn were seeded by :meth:`open` before the tree rebuilt."""

    def update_view(self, view_model: ViewModel) -> None:
        """Re-seeds the open window's controls from where its subject stands."""
        self._view_model = view_model
        self._render()

    @property
    def view_model(self) -> ViewModel:
        """What the window draws.

        Raises:
            SystemError: when the window is drawn before :meth:`open` seeds it.
        """
        if self._view_model is None:
            raise SystemError(f"The {self._subject} window is drawn from a view model it was opened with")

        return self._view_model

    @abstractmethod
    def _render(self) -> None:
        """Draws the controls from the seeded view model."""
