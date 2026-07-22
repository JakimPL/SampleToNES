from dataclasses import dataclass
from typing import Optional, Tuple, Union

from sampletones_application.view_model.shared.history import HistoryDetail

from .action import HistoryAction

CoalesceKey = Tuple[Union[str, int], ...]


@dataclass
class PendingTransaction:
    """The open transaction's accumulating state.

    Bundles the gesture being recorded (``action`` and its ``detail`` segments),
    the ``coalesce`` key naming the gesture's target, the nesting ``depth`` of
    coalesced ``transaction()`` scopes, and the count of fine-grained
    ``mutations`` absorbed so far. Keeping these together holds the label,
    detail, target, and mutation tally of one gesture in lockstep. The presence
    of a ``PendingTransaction`` instance is itself the signal that a transaction
    is open, and nesting a coalesced scope increments its ``depth``.
    """

    action: HistoryAction
    detail: HistoryDetail
    coalesce: Optional[CoalesceKey]
    depth: int = 1
    mutations: int = 0
