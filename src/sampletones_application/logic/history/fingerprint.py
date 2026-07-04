from __future__ import annotations

import hashlib
from typing import Callable, Dict, Iterable, List, Tuple

from sampletones_core.project import Project
from sampletones_core.reconstructions import Reconstruction

ReconstructionHash = Callable[[Reconstruction], str]


def fingerprint_project(
    project: Project,
    *,
    reconstruction_hash: ReconstructionHash,
) -> str:
    """Returns a content hash used to verify that a restore reproduces a snapshot.

    The hash covers the full project state; each sample's reconstruction content
    enters through ``reconstruction_hash``, so the caller decides between a
    memoized digest (capture, where copy-on-write keeps it valid) and a fresh one
    (verification, where staleness would mask a divergence).
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
        parts.append(reconstruction_hash(sample.reconstruction))

    combined = "|".join(parts)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


class ReconstructionHashCache:
    """Memoizes per-reconstruction content hashes by object identity.

    Copy-on-write discipline makes a reconstruction's content immutable for the
    object's lifetime, so one hash per object suffices and capture-time
    fingerprinting collapses to hashing the light structure. Each entry stores a
    strong reference to its reconstruction alongside the digest: the reference
    keeps the object alive, so its ``id()`` can never be recycled onto a
    different object while the entry exists. :meth:`prune` drops entries for
    reconstructions that no longer appear in any given project, releasing the
    references and bounding the cache by what the history retains.
    """

    def __init__(self, *, reconstruction_hash: ReconstructionHash) -> None:
        self._reconstruction_hash = reconstruction_hash
        self._hashes: Dict[int, Tuple[Reconstruction, str]] = {}

    def hash(self, reconstruction: Reconstruction) -> str:
        key = id(reconstruction)
        cached = self._hashes.get(key)
        if cached is None:
            cached = (reconstruction, self._reconstruction_hash(reconstruction))
            self._hashes[key] = cached

        return cached[1]

    def prune(self, projects: Iterable[Project]) -> None:
        live = {id(sample.reconstruction) for project in projects for sample in project.samples}
        self._hashes = {key: value for key, value in self._hashes.items() if key in live}
