from typing import Protocol, Tuple

from sampletones_application.logic.main.sources.key import SourceKey
from sampletones_application.logic.main.sources.recording import Recording


class SourceRow(Protocol):
    """One row of the list a run is set up in.

    A row is either a recording the reader named or a folder standing for the recordings gathered
    below it, and both answer the same three questions: what a gesture names it by, which
    recordings it stands for, and how many those are. Every reader works through those answers, so
    the two kinds are told apart in one place — the kind a key carries — rather than at each site
    that walks the list.
    """

    @property
    def key(self) -> SourceKey: ...

    @property
    def recordings(self) -> Tuple[Recording, ...]: ...

    @property
    def count(self) -> int: ...
