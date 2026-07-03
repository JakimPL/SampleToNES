from dataclasses import dataclass
from typing import Tuple

from sampletones_application.view_model.sequencer.history import HistoryDetailSegment

from .action import HistoryAction


@dataclass
class PendingTransaction:
    """The open transaction's accumulating state.

    Bundles the gesture being recorded (``action`` and its ``detail`` segments),
    the nesting ``depth`` of coalesced ``transaction()`` scopes, and the count of
    fine-grained ``mutations`` absorbed so far. Keeping these together means the
    label, detail, and mutation tally of one gesture can never drift apart. The
    presence of a ``PendingTransaction`` instance is itself the signal that a
    transaction is open; nesting adds depth rather than a second instance.
    """

    action: HistoryAction
    detail: Tuple[HistoryDetailSegment, ...]
    depth: int = 1
    mutations: int = 0
