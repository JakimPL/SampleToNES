from dataclasses import dataclass
from typing import Optional, TypeVar, Union

import numpy as np

from .violations import ViolationKind


@dataclass(frozen=True)
class Opened:
    stream: int
    device: int
    sample_rate: int
    frames_per_buffer: Optional[int]
    thread: str


@dataclass(frozen=True)
class Refused:
    device: int
    reason: str
    thread: str


@dataclass(frozen=True, eq=False)
class Written:
    stream: int
    samples: np.ndarray
    thread: str


@dataclass(frozen=True)
class Drained:
    stream: int
    thread: str


@dataclass(frozen=True)
class Closed:
    stream: int
    discarded: int
    thread: str


@dataclass(frozen=True)
class Terminated:
    driver: int
    thread: str


@dataclass(frozen=True)
class Violation:
    kind: ViolationKind
    stream: Optional[int]
    thread: str


TimelineEvent = Union[Opened, Refused, Written, Drained, Closed, Terminated, Violation]
EventT = TypeVar("EventT", Opened, Refused, Written, Drained, Closed, Terminated, Violation)
