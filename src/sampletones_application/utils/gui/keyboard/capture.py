from typing import Optional, Tuple

from sampletones_application.utils.gui.keyboard.combination import KeyCombination
from sampletones_application.utils.gui.keyboard.event import KeyEvent
from sampletones_application.utils.gui.keyboard.keys import is_named_key
from sampletones_application.utils.gui.keyboard.modifiers import is_modifier_key
from sampletones_application.utils.gui.keyboard.router import KeyRouter
from sampletones_shared.types.callback import Callback, VoidCallback
from sampletones_shared.utils.callbacks import CallbackMixin


class KeyCapture(CallbackMixin):
    """Reads one combination straight from the keyboard, for an editor assigning keys by press.

    While it listens it sits on top of the router's modal stack, above the dialog that armed it, so
    every press reaches here and the dialog's own navigation keys stay out of the way of a reader
    pressing Tab or Enter as the combination they want. Listening ends with the first press that
    names a key: the cancel combination the capture was given reports nothing, anything else reports
    the combination it spells.

    A press the key table names none of leaves the capture listening, and so does a modifier held on
    its own: a modifier is what a combination is reached with, and a binding is kept as the name its
    keys read under, so the reader presses again and the combination they meant is the one read.

    Args:
        key_router: The router whose modal stack the capture claims while it listens.
        cancel: The combinations that end the capture, which a dialog reads from its own scheme.
    """

    def __init__(
        self,
        *,
        key_router: KeyRouter,
        cancel: Tuple[KeyCombination, ...],
    ) -> None:
        self._router = key_router
        self._cancel = cancel
        self._listening = False

        self.on_captured: Optional[Callback] = None
        self.on_cancelled: Optional[VoidCallback] = None

    @property
    def is_listening(self) -> bool:
        """Whether the capture holds the keyboard, waiting for the press to read."""
        return self._listening

    def start(self) -> None:
        """Takes the keyboard, leaving a capture already listening as it stands."""
        if self._listening:
            return

        self._listening = True
        self._router.push_modal(self)

    def stop(self) -> None:
        """Gives the keyboard back to the dialog beneath, once per claim."""
        if not self._listening:
            return

        self._listening = False
        self._router.pop_modal()

    def handle_key(self, event: KeyEvent) -> None:
        """Reads the press, reporting the combination it names once one arrives."""
        if is_modifier_key(event.key) or not is_named_key(event.key):
            return

        combination = KeyCombination(event.key, event.modifiers)
        self.stop()
        if combination in self._cancel:
            self.call(self.on_cancelled)
            return

        self.call(self.on_captured, combination)
