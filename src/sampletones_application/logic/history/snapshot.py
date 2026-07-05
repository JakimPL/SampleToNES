from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from sampletones_application.view_model.shared.history import HistoryDetail
from sampletones_core.project import Project

from .action import HistoryAction


def snapshot_project(project: Project) -> Project:
    """Captures an independent copy of a project that shares reconstruction audio.

    The song, settings, metadata and sample shells are deep-copied so later edits
    to the live project leave the snapshot untouched. Each sample's reconstruction
    is shared by reference: reconstruction edits are copy-on-write (they install a
    fresh reconstruction rather than mutating in place), so a shared reconstruction
    stays valid for the life of the snapshot while the multi-megabyte audio arrays
    are never duplicated.
    """
    shared_reconstructions: Dict[int, object] = {
        id(sample.reconstruction): sample.reconstruction for sample in project.samples
    }
    return copy.deepcopy(project, shared_reconstructions)


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
