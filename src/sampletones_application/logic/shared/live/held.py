from typing import List, Optional

from .key import LiveKey
from .strike import Strike


class HeldKeys:
    """The keys held down while keys are played live, and the press the sound follows.

    One note sounds at a time, and the newest press stands in front. Lifting the key in front returns to the
    most recent key still held, which strikes again, and lifting a key behind it changes nothing heard. A
    lift that ends no note, a computer key's recording, leaves its press in front playing to its end. The
    sustain pedal keeps the press in front sounding once its key lifts, and as the pedal comes up the lift
    takes effect.
    """

    def __init__(self, *, sustained: bool) -> None:
        """Starts with no key down.

        Args:
            sustained: Whether the sustain pedal is down.
        """
        self._held: List[Strike] = []
        self._front: Optional[Strike] = None
        self._sustained = sustained

    @property
    def front(self) -> Optional[Strike]:
        """The press the sound follows, or ``None`` once the note it struck has ended."""
        return self._front

    @property
    def holds(self) -> bool:
        """Whether any key is down."""
        return bool(self._held)

    def press(self, strike: Strike) -> None:
        """Puts ``strike`` in front, its key held above every other; a key pressed again moves up."""
        self._held = [held for held in self._held if held.key != strike.key]
        self._held.append(strike)
        self._front = strike

    def release(self, key: LiveKey) -> None:
        """Lifts ``key``, whose note ends where it stands in front, unless the pedal holds it."""
        lifted = next((held for held in self._held if held.key == key), None)
        if lifted is None:
            return

        self._held.remove(lifted)
        if lifted is self._front and not self._sustained:
            self._lift_front()

    def pedal(self, down: bool) -> None:
        """Takes the pedal's state; as it comes up, a press in front whose key lifted meanwhile lifts."""
        self._sustained = down
        if not down and self._front is not None and self._front not in self._held:
            self._lift_front()

    def _lift_front(self) -> None:
        """Hands the front to the most recent key still held, or to nothing, unless its note plays to its end."""
        if self._front is not None and not self._front.ends_on_release:
            return

        self._front = self._held[-1] if self._held else None
