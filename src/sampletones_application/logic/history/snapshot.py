from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sampletones_application.view_model.shared.history import HistoryDetail
from sampletones_core.project import Project

from .action import HistoryAction


@dataclass(frozen=True)
class HistoryEntry:
    """One committed state in the history stack.

    ``project`` is the captured snapshot restored on undo/redo. ``fingerprint`` is
    populated only under strict deployment, where it powers restore verification;
    production leaves it ``None`` to avoid the hashing cost on every edit.
    """

    project: Project
    action: HistoryAction
    created: datetime
    detail: HistoryDetail = field(default_factory=tuple)
    fingerprint: Optional[str] = None
