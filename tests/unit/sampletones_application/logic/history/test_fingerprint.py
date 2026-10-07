import copy
from typing import Final, FrozenSet, List

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import HistoryIntegrityError
from sampletones_application.logic.history.fingerprint import (
    ReconstructionHashCache,
    fingerprint_project,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.utils.hashing import hash_model
from tests.conftest import ReconstructionFactory
from tests.suite.history.audit import fresh_fingerprint
from tests.suite.history.perturbation import perturbed_project, project_leaves
from tests.suite.history.projects import every_part_project
from tests.unit.sampletones_application.logic.history.conftest import HistoryFactory

REACHED_LABELS: Final[FrozenSet[str]] = frozenset(
    {
        "Metadata.version",
        "ProjectInfo.title",
        "ProjectInfo.modified",
        "ProjectSettings.tempo",
        "Song.rows_per_pattern",
        "Song.order[]{}",
        "Row.volume",
        "Note.value",
        "Step.value",
        "NoteOn.voice_id",
        "Sample.name",
        "Reconstruction.coefficient",
        "PulseInstruction.volume",
        "NoiseInstruction.period",
        "InstructionsItem.initial_pitch",
        "ChannelAssignment.stem_ids[]",
        "StemsData.scale",
        "StemSettings.channels[]",
        "Instrument.name",
        "Instrument.initial_period",
    }
)


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
        snapshot = project_controller.project.snapshot()

        assert fingerprint_project(snapshot, reconstruction_hash=hash_model) == original

    def test_fingerprint_changes_with_state(
        self,
        project_controller: ProjectController,
    ) -> None:
        before = fingerprint_project(
            project_controller.project,
            reconstruction_hash=hash_model,
        )

        project_controller.set_tempo(project_controller.project.settings.tempo + 7)

        assert fingerprint_project(project_controller.project, reconstruction_hash=hash_model) != before


class TestFingerprintCompleteness:
    """A change to any field a project holds reaches the fingerprint, so the history audit is blind nowhere."""

    def test_every_field_reaches_the_fingerprint(self) -> None:
        project = every_part_project()
        baseline = fresh_fingerprint(project)

        blind = [
            leaf.label
            for leaf in project_leaves(project)
            if fresh_fingerprint(perturbed_project(project, leaf)) == baseline
        ]

        assert blind == []

    def test_the_walk_reaches_every_kind_of_part(self) -> None:
        labels = {leaf.label for leaf in project_leaves(every_part_project())}

        assert REACHED_LABELS <= labels

    def test_an_independent_copy_keeps_the_fingerprint(self) -> None:
        project = every_part_project()

        assert fresh_fingerprint(copy.deepcopy(project)) == fresh_fingerprint(project)

    def test_mappings_in_another_order_keep_the_fingerprint(self) -> None:
        project = every_part_project()
        baseline = fresh_fingerprint(project)

        project.song.order = [dict(reversed(list(frame.items()))) for frame in project.song.order]
        project.song.channels = dict(reversed(list(project.song.channels.items())))

        assert fresh_fingerprint(project) == baseline


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
        kept = project_controller.add_sample(reconstruction_factory(), name="kept").reconstruction
        discarded = reconstruction_factory()
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

        object.__setattr__(sample.reconstruction, "coefficient", sample.reconstruction.coefficient + 1.0)

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

        with history.transaction(HistoryAction.REMOVE_VOICE):
            controller.remove_voice(sample.id)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        assert history._hash_cache is not None
        assert len(history._hash_cache._hashes) == 0
