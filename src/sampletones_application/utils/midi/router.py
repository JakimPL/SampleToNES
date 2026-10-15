import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, Tuple

from sampletones_application.utils.midi.messages import (
    MidiAllNotesOff,
    MidiMessage,
    MidiNoteOff,
    MidiNoteOn,
    MidiPedal,
)

ActivePredicate = Callable[[], bool]
PedalTarget = Callable[[bool], None]


class MidiTarget(Protocol):
    """What a scope does with the keys it takes, on the thread the message arrived on."""

    def press(self, note: int, velocity: int, /) -> None: ...

    def lift(self, note: int, /) -> None: ...


@dataclass(frozen=True)
class _Scope:
    priority: int
    active: ActivePredicate
    target: MidiTarget


class MidiRouter:
    """The one dispatcher of the MIDI keyboard's keys, offering each to the scopes the way the key router does.

    Every consumer registers a scope with a priority and an ``active`` predicate. Whether a scope is active
    is a question about the interface, which only the render thread may ask, so the render thread publishes
    the active scopes once a frame, and a key arriving on the MIDI library's thread reads the latest
    publication. A key goes to the highest active scope, and none takes it while no scope is active.

    A key lifted reaches the scope that took its press, whatever is active by then, so a tab switched or a
    dialog opened while a key is down leaves no note hanging. Letting every key go lifts each one held
    through the scope that took it. The sustain pedal belongs to the sound alone, so it goes to the one
    pedal target, whichever scope is active.

    Each target is called on the thread the message arrived on, so a target that sounds acts at once, and
    a target that changes the interface hands its work to the render thread itself.
    """

    def __init__(self) -> None:
        self._scopes: List[_Scope] = []
        self._published: Tuple[_Scope, ...] = ()
        self._lock = threading.Lock()
        self._held: Dict[int, MidiTarget] = {}
        self._pedal: Optional[PedalTarget] = None

    def register(
        self,
        target: MidiTarget,
        *,
        priority: int,
        active: ActivePredicate,
    ) -> None:
        """Adds a scope, keeping the scopes ordered from highest priority to lowest.

        Args:
            target: What takes the keys the scope takes.
            priority: The scope's rank; the highest active scope takes a key.
            active: Whether the scope takes keys now, asked on the render thread alone.
        """
        self._scopes.append(_Scope(priority=priority, active=active, target=target))
        self._scopes.sort(key=lambda scope: scope.priority, reverse=True)

    def take_pedal(self, target: PedalTarget) -> None:
        """Makes ``target`` the one the sustain pedal reaches."""
        self._pedal = target

    def publish(self) -> None:
        """Asks every scope whether it is active, on the render thread, for the keys arriving from now on."""
        published = tuple(scope for scope in self._scopes if scope.active())
        with self._lock:
            self._published = published

    def route(self, message: MidiMessage) -> None:
        """Hands ``message`` to the scope it belongs to, on the calling thread."""
        match message:
            case MidiNoteOn(note=note, velocity=velocity):
                self._press(note, velocity)
            case MidiNoteOff(note=note):
                self._lift(note)
            case MidiPedal(down=down):
                if self._pedal is not None:
                    self._pedal(down)
            case MidiAllNotesOff():
                self._lift_every_key()

    def _press(self, note: int, velocity: int) -> None:
        """Hands a press to the highest active scope, lifting the key first where another scope still holds it."""
        with self._lock:
            scope = self._published[0] if self._published else None
            previous = self._held.get(note) if scope is not None else None
            if scope is not None:
                self._held[note] = scope.target

        if previous is not None and scope is not None and previous is not scope.target:
            previous.lift(note)

        if scope is not None:
            scope.target.press(note, velocity)

    def _lift(self, note: int) -> None:
        with self._lock:
            target = self._held.pop(note, None)

        if target is not None:
            target.lift(note)

    def _lift_every_key(self) -> None:
        with self._lock:
            held, self._held = self._held, {}

        for note, target in held.items():
            target.lift(note)
