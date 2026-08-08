from typing import Optional

from sampletones_application.utils.gui.shortcuts.ids import ShortcutId
from sampletones_application.utils.gui.shortcuts.scheme import ShortcutScheme
from sampletones_application.utils.gui.shortcuts.shortcut import Shortcut
from sampletones_shared.types.callback import Callback
from sampletones_shared.utils.callbacks import CallbackMixin


class ShortcutSource(CallbackMixin):
    """The scheme every action resolves its keys against, and the one place it changes.

    A menu asks it what accelerator to print and a dispatcher asks it what a press means, so
    activating another scheme rebinds the whole application from one call. Whatever has already
    read a combination is refreshed by the listener on ``on_bindings_changed``.
    """

    def __init__(self, scheme: ShortcutScheme) -> None:
        self._scheme = scheme
        self.on_bindings_changed: Optional[Callback] = None

    @property
    def scheme(self) -> ShortcutScheme:
        return self._scheme

    def shortcut(self, shortcut_id: ShortcutId) -> Shortcut:
        """The binding the scheme in place gives an action."""
        return self._scheme.shortcut(shortcut_id)

    def display(self, shortcut_id: ShortcutId) -> str:
        """The combination an action reads under, as a menu or a tooltip prints it."""
        return self.shortcut(shortcut_id).display()

    def activate(self, scheme: ShortcutScheme) -> None:
        """Make ``scheme`` the one every action resolves its keys against.

        Announces the change once the swap is in place, so the listener reads the new combinations
        as it rebinds. Activating the scheme already in place leaves both the keys and the listener
        untouched.
        """
        if scheme == self._scheme:
            return

        self._scheme = scheme
        self.call(self.on_bindings_changed, scheme)
