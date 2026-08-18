from abc import ABC
from typing import Final, List, Optional

from sampletones_application.tags.general import TAG_GLOBAL_THEME_DIALOG
from sampletones_application.ui.elements.window import GUIWindow
from sampletones_application.ui.themes.registry import ThemeRegistry
from sampletones_application.utils.gui.dialog_navigation import (
    DialogKeyboardNavigator,
    FocusStop,
)
from sampletones_application.utils.gui.keyboard import KeyRouter
from sampletones_application.utils.gui.shortcuts.source import ShortcutSource
from sampletones_shared.types.callback import VoidCallback

INITIAL_FOCUS_STOP: Final[int] = 0


class GUIDialogWindow(GUIWindow, ABC):
    """A ``GUIWindow`` whose controls answer to Tab, Enter and Escape while it stands.

    The keyboard claim belongs to the appearance rather than to the dialog: a window names its
    stops as it builds its tree, and the navigator installed over them is released when that tree
    is deleted. Every reopen wires a fresh one, which is what holds the ring and the tree it reads
    in step across a rebuild.

    A dialog states the router and the scheme its navigation reads, so which keys cycle, activate
    and cancel follow the reader's own bindings.
    """

    def __init__(
        self,
        tag: str,
        width: int,
        height: int,
        *,
        key_router: KeyRouter,
        shortcut_source: ShortcutSource,
    ) -> None:
        self._router = key_router
        self._shortcuts = shortcut_source
        self._navigator: Optional[DialogKeyboardNavigator] = None

        super().__init__(
            tag,
            width,
            height,
        )

    def _install_navigation(
        self,
        stops: List[FocusStop],
        *,
        on_escape: VoidCallback,
        initial_index: int = INITIAL_FOCUS_STOP,
    ) -> None:
        """Wires Tab, Enter and Escape over the controls this appearance offers.

        Args:
            stops: The controls the focus ring cycles, in reading order.
            on_escape: What cancelling this dialog means.
            initial_index: The stop focus opens on, which points a prompt at the answer it expects.
        """
        self._navigator = DialogKeyboardNavigator(
            window_tag=self.tag,
            stops=stops,
            on_escape=on_escape,
            key_router=self._router,
            shortcut_source=self._shortcuts,
            initial_index=initial_index,
        )
        self._navigator.install()

    def _bind_dialog_theme(self, *tags: str) -> None:
        """Gives each named control the field styling a dialog's own surface reads."""
        theme = ThemeRegistry.get(TAG_GLOBAL_THEME_DIALOG)
        for tag in tags:
            theme.bind_to_item(tag)

    def _teardown(self) -> None:
        """Releases the keyboard claim of the appearance being torn down."""
        if self._navigator is not None:
            self._navigator.dispose()
            self._navigator = None
