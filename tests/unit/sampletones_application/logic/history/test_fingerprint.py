from typing import List

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import HistoryIntegrityError
from sampletones_application.logic.history.fingerprint import ReconstructionHashCache, fingerprint_project
from sampletones_application.logic.history.snapshot import snapshot_project
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.utils.serialization import hash_model
from tests.conftest import ReconstructionFactory
from tests.unit.sampletones_application.logic.history.conftest import HistoryFactory


class CountingHash:
    def __init__(self) -> None:
        self.calls: List[Reconstruction] = []

    def __call__(self, reconstruction: Reconstruction) -> str:
        self.calls.append(reconstruction)
        return hash_model(reconstruction)


class TestFingerprint:
    def test_fingerprint_stable_across_snapshot(
        self,
        project_controller: ProjectController,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project_controller.add_sample(reconstruction_factory(), name="lead")

        original = fingerprint_project(project_controller.project, reconstruction_hash=hash_model)
        snapshot = snapshot_project(project_controller.project)

        assert fingerprint_project(snapshot, reconstruction_hash=hash_model) == original

    def test_fingerprint_changes_with_state(self, project_controller: ProjectController) -> None:
        before = fingerprint_project(project_controller.project, reconstruction_hash=hash_model)

        project_controller.set_tempo(project_controller.project.settings.tempo + 7)

        assert fingerprint_project(project_controller.project, reconstruction_hash=hash_model) != before


class TestHashCache:
    def test_hash_computed_once_per_reconstruction_object(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting = CountingHash()
        cache = ReconstructionHashCache(reconstruction_hash=counting)
        reconstruction = reconstruction_factory()

        first = cache.hash(reconstruction)
        second = cache.hash(reconstruction)

        assert first == second
        assert counting.calls == [reconstruction]

    def test_distinct_reconstructions_hash_independently(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting = CountingHash()
        cache = ReconstructionHashCache(reconstruction_hash=counting)
        first = reconstruction_factory()
        second = reconstruction_factory()

        cache.hash(first)
        cache.hash(second)

        assert counting.calls == [first, second]

    def test_prune_drops_hashes_for_discarded_reconstructions(
        self,
        project_controller: ProjectController,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting = CountingHash()
        cache = ReconstructionHashCache(reconstruction_hash=counting)
        kept = reconstruction_factory()
        discarded = reconstruction_factory()
        project_controller.add_sample(kept, name="kept")
        cache.hash(kept)
        cache.hash(discarded)

        cache.prune([project_controller.project])

        cache.hash(kept)
        cache.hash(discarded)
        assert counting.calls == [kept, discarded, discarded]


class TestStrictManagerFingerprinting:
    def test_capture_memoized_restore_verified_fresh(
        self,
        history_factory: HistoryFactory,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """Walks gestures and restores under strict verification as the oracle.

        Every commit fingerprints through the memo and every restore recomputes
        fresh hashes; any disagreement between the two paths would raise
        ``HistoryIntegrityError`` during the walk.
        """
        controller, history = history_factory()
        with history.transaction(HistoryAction.ADD_SAMPLE):
            controller.add_sample(reconstruction_factory(), name="lead")
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        history.undo()
        history.undo()
        history.redo()
        history.jump_to(2)

        assert controller.project.settings.tempo == 150

    def test_restore_raises_on_mutated_snapshot_shared_state(
        self,
        history_factory: HistoryFactory,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """Proves memoization leaves the copy-on-write tripwire intact.

        Mutating a stored snapshot's shared reconstruction in place keeps the
        object's identity, so a memoized verification would reproduce the stale
        digest and pass; the fresh verification hash diverges from the recorded
        fingerprint and raises.
        """
        controller, history = history_factory()
        with history.transaction(HistoryAction.ADD_SAMPLE):
            sample = controller.add_sample(reconstruction_factory(), name="lead")
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        sample.reconstruction.coefficient = sample.reconstruction.coefficient + 1.0

        with pytest.raises(HistoryIntegrityError):
            history.undo()

    def test_eviction_prunes_cache_to_retained_reconstructions(
        self,
        history_factory: HistoryFactory,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        controller, history = history_factory(budget=2)
        with history.transaction(HistoryAction.ADD_SAMPLE):
            sample = controller.add_sample(reconstruction_factory(), name="lead")
        with history.transaction(HistoryAction.REMOVE_SAMPLE):
            controller.remove_sample(sample.id)
        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert history._hash_cache is not None
        assert len(history._hash_cache._hashes) == 0
