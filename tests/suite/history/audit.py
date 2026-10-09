from collections.abc import Hashable
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, Iterator, List, Optional, Protocol, Sequence, Tuple

import numpy as np

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.fingerprint import ReconstructionHashCache, fingerprint_project
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.constants.enums import ChannelName
from sampletones_core.project import Project
from sampletones_core.project.voices.instrument import Instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.types.callback import VoidCallback
from sampletones_shared.utils.hashing import hash_model

Settle = Callable[[VoidCallback], None]
CommitKey = Tuple[HistoryAction, Hashable]


def fresh_fingerprint(project: Project) -> str:
    """The project's whole state, every reconstruction hashed afresh rather than through a memo."""
    return fingerprint_project(project, reconstruction_hash=hash_model)


def immediately(gesture: VoidCallback) -> None:
    """Runs a gesture whose whole effect lands before it returns."""
    gesture()


class HistoryDoors(Protocol):
    """The gestures that move through the history, as the tier under test reaches them."""

    def undo(self) -> None: ...

    def redo(self) -> None: ...

    def jump_to(self, index: int) -> None: ...


@dataclass(frozen=True)
class ExpectedEntry:
    action: HistoryAction
    fingerprint: str


@dataclass
class StackModel:
    """The history's rules restated plainly: the stack a correct history holds after each step.

    A commit appends past the cursor and drops the redo branch. A commit naming the action and
    target of the commit before it replaces the top entry instead, while the cursor stands on the
    top, nothing was restored since, and the top is not the save point. A save marks the cursor,
    and the budget drops the oldest entries, taking the save point along when it falls out.
    """

    budget: int
    entries: List[ExpectedEntry] = field(default_factory=list)
    cursor: int = -1
    saved: Optional[int] = None
    last_key: Optional[CommitKey] = None

    def reset(
        self,
        fingerprint: Optional[str],
        *,
        clean: bool,
    ) -> None:
        self.last_key = None
        if fingerprint is None:
            self.entries = []
            self.cursor = -1
            self.saved = None
            return

        self.entries = [ExpectedEntry(HistoryAction.INITIAL, fingerprint)]
        self.cursor = 0
        self.saved = 0 if clean else None

    def commit(
        self,
        action: HistoryAction,
        target: Optional[Hashable],
        fingerprint: str,
    ) -> None:
        key = (action, target) if target is not None else None
        entry = ExpectedEntry(action, fingerprint)
        if self.continues_run(action, target):
            self.entries[self.cursor] = entry
        else:
            if self.saved is not None and self.saved > self.cursor:
                self.saved = None

            del self.entries[self.cursor + 1 :]
            self.entries.append(entry)
            self.cursor = len(self.entries) - 1
            self._evict()

        self.last_key = key

    def continues_run(
        self,
        action: HistoryAction,
        target: Optional[Hashable],
    ) -> bool:
        """Whether a commit of ``action`` on ``target`` replaces the top entry rather than appending."""
        key = (action, target) if target is not None else None
        return (
            key is not None
            and key == self.last_key
            and self.cursor == len(self.entries) - 1
            and self.cursor != self.saved
        )

    def _evict(self) -> None:
        overflow = len(self.entries) - self.budget
        if overflow <= 0:
            return

        del self.entries[:overflow]
        self.cursor -= overflow
        if self.saved is not None:
            self.saved = self.saved - overflow if self.saved >= overflow else None

    def undo(self) -> None:
        if self.cursor > 0:
            self.move(self.cursor - 1)

    def redo(self) -> None:
        if self.cursor < len(self.entries) - 1:
            self.move(self.cursor + 1)

    def move(self, index: int) -> None:
        if 0 <= index < len(self.entries) and index != self.cursor:
            self.cursor = index
            self.last_key = None

    def save(self) -> None:
        self.saved = self.cursor

    @property
    def live(self) -> ExpectedEntry:
        return self.entries[self.cursor]


def _same(
    first: object,
    second: object,
) -> bool:
    """Whether two derived views hold the same content, arrays compared element by element."""
    if isinstance(first, np.ndarray) and isinstance(second, np.ndarray):
        return first.shape == second.shape and bool(np.array_equal(first, second))

    if isinstance(first, dict) and isinstance(second, dict):
        return first.keys() == second.keys() and all(_same(first[key], second[key]) for key in first)

    if isinstance(first, (list, tuple)) and isinstance(second, (list, tuple)):
        return len(first) == len(second) and all(_same(left, right) for left, right in zip(first, second))

    return first == second


def _fresh_reconstruction(reconstruction: Reconstruction) -> Reconstruction:
    """The same fields in a new object, whose every derived view is read afresh."""
    return Reconstruction.model_construct(**dict(reconstruction))


def stale_reconstruction_views(reconstruction: Reconstruction) -> List[str]:
    """The derived views of a reconstruction that disagree with the ones its fields give afresh."""
    fresh = _fresh_reconstruction(reconstruction)
    views = {
        "streams": (reconstruction.streams, fresh.streams),
        "instructions": (reconstruction.instructions, fresh.instructions),
        "initial_pitches": (reconstruction.initial_pitches, fresh.initial_pitches),
        "held_features": (reconstruction.held_features, fresh.held_features),
        "playing_channels": (reconstruction.playing_channels, fresh.playing_channels),
    }
    return [name for name, (held, recomputed) in views.items() if not _same(held, recomputed)]


def stale_instrument_channels(instrument: Instrument) -> List[ChannelName]:
    """The channels whose memoized frames disagree with the frames the envelopes give afresh."""
    fresh = instrument.model_copy()
    fresh.invalidate()
    return [
        channel_name
        for channel_name in ChannelName.items()
        if not _same(instrument.instructions(channel_name), fresh.instructions(channel_name))
    ]


def voices_index_faults(project: Project) -> List[str]:
    """Where the voices collection's lookups disagree with the order it iterates in."""
    faults: List[str] = []
    voices = project.voices
    for position, voice in enumerate(voices):
        if voices[position] is not voice:
            faults.append(f"position {position} answers another voice than {voice.name!r}")

        if voices.get(voice.id) is not voice:
            faults.append(f"id of {voice.name!r} answers another voice")
            continue

        if voices.get_index(voice.id) != position:
            faults.append(f"id of {voice.name!r} answers position {voices.get_index(voice.id)}")

    return faults


def derived_faults(projects: Sequence[Project]) -> List[str]:
    """Every derived view in the projects that disagrees with what its fields give afresh.

    Entries share voices and reconstructions, so each object is read once however many
    projects hold it.
    """
    faults: List[str] = []
    voices = {id(voice): voice for project in projects for voice in project.voices}
    for voice in voices.values():
        match voice:
            case Sample():
                stale = stale_reconstruction_views(voice.reconstruction)
                faults.extend(f"{voice.name!r} holds a stale {name}" for name in stale)
            case Instrument():
                channels = stale_instrument_channels(voice)
                faults.extend(f"{voice.name!r} holds stale {channel} frames" for channel in channels)

    return faults


class HistoryAudit:
    """Holds a history to its rules and to the states it recorded, after every step a case takes.

    The audit keeps its own model of the stack (:class:`StackModel`) and reads each expected state
    from the live project right after the gesture that made it, hashing every reconstruction
    afresh. After every step it asserts that the live project is the state at the cursor, that
    every stored entry still holds exactly the state it recorded, so each value shared between
    entries stands as it was, that derived views agree with their fields, that the voices
    collection finds each voice where it iterates it, and that the stack's shape and the dirty
    flag follow the model.

    Each step runs through ``settle``, which returns once everything the step started has landed:
    a worker's report as well as the gesture itself. Each of ``observers`` asserts what the tier
    under test adds to every check, such as the voice a tab shows.
    """

    def __init__(
        self,
        controller: ProjectController,
        history: HistoryManager,
        *,
        budget: int,
        doors: HistoryDoors,
        settle: Settle,
        observers: Sequence[VoidCallback],
    ) -> None:
        self._controller = controller
        self._history = history
        self._doors = doors
        self._settle = settle
        self._observers = observers
        self.model = StackModel(budget=budget)
        self.observe_reset()

    def observe_reset(self) -> None:
        """Takes the stack a project transition left as the new baseline, after checking it."""
        fingerprint = fresh_fingerprint(self._controller.project) if self._controller.is_open else None
        self.model.reset(fingerprint, clean=not self._controller.is_dirty)
        self.check()

    def transition(self, gesture: VoidCallback) -> None:
        """Runs a new, open or close and takes the stack it leaves as the new baseline."""
        self._settle(gesture)
        self.observe_reset()

    def perform(
        self,
        gesture: VoidCallback,
        *,
        action: HistoryAction,
        target: Optional[Hashable],
    ) -> None:
        """Runs a gesture that changes the project and checks the one commit it records.

        ``target`` names what the gesture changes as the history's coalescing sees it: two
        gestures of one action and one target in a row make one entry.
        """
        self.check()
        before = fresh_fingerprint(self._controller.project)
        self._settle(gesture)
        after = fresh_fingerprint(self._controller.project)
        assert after != before, f"A {action} gesture left the project as it stood"
        self.model.commit(action, target, after)
        self.check()

    def attempt(
        self,
        gesture: VoidCallback,
        *,
        action: HistoryAction,
        target: Optional[Hashable],
    ) -> None:
        """Runs a gesture the state before it may leave nothing to change, and checks what it records.

        A gesture that changes the project records its one commit, and one that leaves it as it
        stood records nothing. A pair of gestures reaches this where the first leaves the second
        nothing to act on, such as a transpose over a block a cut has emptied.
        """
        self.check()
        before = fresh_fingerprint(self._controller.project)
        self._settle(gesture)
        after = fresh_fingerprint(self._controller.project)
        if after != before:
            self.model.commit(action, target, after)

        self.check()

    def refused(self, gesture: VoidCallback) -> None:
        """Runs a gesture meant to leave the project as it stands, and checks the history stays as it was."""
        self.check()
        self._settle(gesture)
        self.check()

    @contextmanager
    def settling(self, settle: Settle) -> Iterator[None]:
        """Runs the steps inside the scope through ``settle``, such as one leaving a worker's report held."""
        standing = self._settle
        self._settle = settle
        try:
            yield
        finally:
            self._settle = standing

    def adopt_landed(self, actions: Sequence[Tuple[HistoryAction, Optional[Hashable]]]) -> None:
        """Takes commits that landed together, out of the case's sight, as the stack now records them.

        Work held back and then released lands several commits at once, so the states between them
        never stand live. Their order and their actions are what the case states. Each state is read
        from the entry recording it, and every later restore is then held to it. The case states
        what else the release did, such as an undo that waited for the edits, before the next check.
        """
        for action, target in actions:
            index = self.model.cursor if self.model.continues_run(action, target) else self.model.cursor + 1
            self.model.commit(action, target, fresh_fingerprint(self._history.entries[index].project))

    def undo(self) -> None:
        self._settle(self._doors.undo)
        self.model.undo()
        self.check()

    def redo(self) -> None:
        self._settle(self._doors.redo)
        self.model.redo()
        self.check()

    def jump_to(self, index: int) -> None:
        self._settle(lambda: self._doors.jump_to(index))
        self.model.move(index)
        self.check()

    def save(self, gesture: VoidCallback) -> None:
        """Runs a save, which makes the state at the cursor the one on disk."""
        self._settle(gesture)
        self.model.save()
        self.check()

    def walk(self) -> None:
        """Visits every entry from the cursor to the first, then to the last, then back again."""
        start = self.model.cursor
        while self.model.cursor > 0:
            self.undo()

        while self.model.cursor < len(self.model.entries) - 1:
            self.redo()

        self.jump_to(0)
        self.jump_to(len(self.model.entries) - 1)
        self.jump_to(start)

    def check(self) -> None:
        self._check_shape()
        hashes = ReconstructionHashCache(reconstruction_hash=hash_model)
        projects = [entry.project for entry in self._history.entries]
        if self._controller.is_open:
            projects.append(self._controller.project)

        self._check_entries(hashes)
        for project in projects:
            assert not voices_index_faults(project), voices_index_faults(project)

        assert not derived_faults(projects), derived_faults(projects)
        if self._controller.is_open:
            self._check_live(hashes)

        for observer in self._observers:
            observer()

    def _check_shape(self) -> None:
        recorded = [entry.action for entry in self._history.entries]
        expected = [entry.action for entry in self.model.entries]
        assert recorded == expected, f"The history holds {recorded} where {expected} belongs"
        assert (
            self._history.cursor == self.model.cursor
        ), f"The cursor stands at {self._history.cursor} where {self.model.cursor} belongs"
        assert self._history.can_undo == (self.model.cursor > 0)
        assert self._history.can_redo == (self.model.cursor < len(self.model.entries) - 1)

    def _check_entries(self, hashes: ReconstructionHashCache) -> None:
        for index, (entry, expected) in enumerate(zip(self._history.entries, self.model.entries)):
            fingerprint = fingerprint_project(entry.project, reconstruction_hash=hashes.hash)
            assert (
                fingerprint == expected.fingerprint
            ), f"Entry {index} ({entry.action}) no longer holds the state it recorded"

    def _check_live(self, hashes: ReconstructionHashCache) -> None:
        fingerprint = fingerprint_project(self._controller.project, reconstruction_hash=hashes.hash)
        assert (
            fingerprint == self.model.live.fingerprint
        ), f"The live project differs from entry {self.model.cursor} ({self.model.live.action})"
        dirty = self._controller.is_dirty
        assert dirty == (self.model.cursor != self.model.saved), (
            f"The project reads {'dirty' if dirty else 'clean'} at entry {self.model.cursor} "
            f"with the save point at {self.model.saved}"
        )
