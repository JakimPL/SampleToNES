from dataclasses import dataclass, field
from typing import List, Optional

from sampletones_shared.types.callback import VoidCallback


@dataclass
class MutationBatch:
    """The open batch's accumulating state.

    Bundles the nesting ``depth`` of coalesced ``batch()`` scopes, the
    ``announcements`` the mutations raised in the order they first arose, and
    whether the project still needs its dirty ``stamp``. Keeping these together
    holds one gesture's deferred notifications in lockstep. The presence of a
    ``MutationBatch`` instance is itself the signal that a batch is open, and
    nesting a scope increments its ``depth``.
    """

    depth: int = 1
    announcements: List[Optional[VoidCallback]] = field(default_factory=list)
    stamped: bool = False

    def record(self, announcement: Optional[VoidCallback]) -> None:
        """Keeps an announcement for the flush, once per distinct signal."""
        if announcement not in self.announcements:
            self.announcements.append(announcement)
