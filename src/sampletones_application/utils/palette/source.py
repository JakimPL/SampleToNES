from typing import Optional

from sampletones_application.utils.palette.palette import Palette
from sampletones_shared.types.callback import Callback
from sampletones_shared.utils.callbacks import CallbackMixin


class PaletteSource(CallbackMixin):
    """The palette every color token resolves against, and the one place it changes.

    A :class:`BaseColor` keeps the token it was written as and reads its value from
    here, so activating another palette gives every color in the application a new
    value with no reload and no re-injection. Whatever DearPyGui has already copied is
    repainted by the listener on ``on_palette_changed``.
    """

    def __init__(self, palette: Palette) -> None:
        self._palette = palette
        self.on_palette_changed: Optional[Callback] = None

    @property
    def palette(self) -> Palette:
        return self._palette

    def activate(self, palette: Palette) -> None:
        """Make ``palette`` the one every color token resolves against.

        Announces the change once the swap is in place, so the listener reads the new
        colors as it repaints. Activating the palette already in place leaves both the
        colors and the listener untouched.
        """
        if palette == self._palette:
            return

        self._palette = palette
        self.call(self.on_palette_changed, palette)
