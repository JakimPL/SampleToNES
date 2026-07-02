from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from sampletones_core.project import Project
from sampletones_shared.utils.serialization import hash_model

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


def fingerprint_project(project: Project) -> str:
    """Returns a content hash used to verify that a restore reproduces a snapshot.

    The hash covers the full project state, including reconstruction content, so
    any divergence between a restored project and its recorded snapshot is caught.
    """
    parts: List[str] = [
        project.metadata.model_dump_json(),
        project.info.model_dump_json(),
        project.settings.model_dump_json(),
        project.song.model_dump_json(),
    ]
    for sample in project.samples:
        parts.append(sample.id)
        parts.append(sample.name)
        parts.append(str(sample.loop))
        parts.append(hash_model(sample.reconstruction))

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


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
    detail: Optional[str] = None
    fingerprint: Optional[str] = None
