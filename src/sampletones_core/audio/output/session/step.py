from collections.abc import Hashable
from dataclasses import dataclass
from typing import Generic, Tuple, TypeVar

from sampletones_core.audio.output.ending import Ending
from sampletones_core.audio.output.lifecycle import (
    PlaybackState,
    StreamAction,
    StreamState,
)

KeyT = TypeVar("KeyT", bound=Hashable)


@dataclass(frozen=True)
class EndReport(Generic[KeyT]):
    """The one report a playback sends as it ends."""

    key: KeyT
    ending: Ending


@dataclass(frozen=True)
class Step(Generic[KeyT]):
    """What the thread writing to the device does next, and the end reports it sends first.

    Attributes:
        action: The device call the writer makes next.
        mixed: The playbacks a write mixes, in the order they were claimed.
        reports: The end reports settled for this step, which go out before the action runs.
    """

    action: StreamAction
    mixed: Tuple[KeyT, ...]
    reports: Tuple[EndReport[KeyT], ...]


@dataclass(frozen=True)
class PlaybackSnapshot(Generic[KeyT]):
    """One playback present, the rank it claimed the output at, where its lifecycle stands, and whether a
    command waits for its next read."""

    key: KeyT
    rank: int
    state: PlaybackState
    commanded: bool


@dataclass(frozen=True)
class SessionSnapshot(Generic[KeyT]):
    """Every input the output decides on: the stream's state and every playback present, in claim order.

    Two cores with equal snapshots make the same decision for every later call, which is what lets a case
    take one for the other, and a report state what the output stood at.
    """

    stream: StreamState
    playbacks: Tuple[PlaybackSnapshot[KeyT], ...]
