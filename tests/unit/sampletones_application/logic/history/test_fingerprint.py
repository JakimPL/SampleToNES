import copy
from typing import Final, FrozenSet, Generic, List, Sequence, TypeVar

import pytest

from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.errors import HistoryIntegrityError
from sampletones_application.logic.history.fingerprint import (
    FreshHashes,
    HashCache,
    fingerprint_project,
    hash_reconstruction,
    hash_song,
)
from sampletones_application.logic.project.controller import ProjectController
from sampletones_core.constants.enums import ChannelName
from sampletones_core.instructions import PulseInstruction
from sampletones_core.project import Project
from sampletones_core.project.patterns.pattern import Pattern
from sampletones_core.project.patterns.row import Row
from sampletones_core.project.song import Song
from sampletones_core.reconstructions import Reconstruction
from sampletones_core.reconstructions.reconstruction.instructions import InstructionsItem
from sampletones_shared.utils.hashing import hash_model
from tests.conftest import ReconstructionFactory
from tests.suite.history.audit import fresh_fingerprint
from tests.suite.history.perturbation import perturbed_project, project_leaves
from tests.suite.history.projects import FIRST_PATTERN, SECOND_PATTERN, every_part_project
from tests.unit.sampletones_application.logic.history.conftest import HistoryFactory

REACHED_LABELS: Final[FrozenSet[str]] = frozenset(
    {
        "Metadata.version",
        "ProjectInfo.title",
        "ProjectInfo.modified",
        "ProjectSettings.tempo",
        "Song.rows_per_pattern",
        "Song.order[]{}",
        "Channel.name",
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
EDITED_ROW: Final[Row] = Row(volume=5)
MUTATED_NAME: Final[str] = "mutated"

Value = TypeVar("Value", InstructionsItem, Pattern)


class CountingHash(Generic[Value]):
    """A hash that remembers every value it was asked for."""

    def __init__(self) -> None:
        self.calls: List[Value] = []

    def __call__(self, value: Value) -> str:
        self.calls.append(value)
        return hash_model(value)


def _streams(reconstruction: Reconstruction) -> List[InstructionsItem]:
    return list(reconstruction.instructions_data)


def _patterns(song: Song) -> List[Pattern]:
    """The song's patterns in the order its digest spells them: channels by name, indices ascending."""
    return [
        song.channels[name].patterns[index]
        for name in sorted(song.channels)
        for index in sorted(song.channels[name].patterns)
    ]


def _every_pattern(projects: Sequence[Project]) -> FrozenSet[int]:
    return frozenset(
        id(pattern)
        for project in projects
        for channel in project.song.channels.values()
        for pattern in channel.patterns.values()
    )


def _edited(reconstruction: Reconstruction) -> Reconstruction:
    """The document with its first pulse rebuilt, every other stream and record kept by identity."""
    return reconstruction.with_channel_data(
        ChannelName.PULSE1,
        [PulseInstruction(on=True, pitch=67, volume=11, duty_cycle=1)],
        67,
        (),
        heard=reconstruction.recorded_stem_ids,
    )


def _edit_a_row(song: Song) -> Pattern:
    """Writes one row of the first pulse's first pattern, and gives back the pattern now standing there."""
    song.channels[ChannelName.PULSE1].set_row(FIRST_PATTERN, 0, EDITED_ROW)
    return song.channels[ChannelName.PULSE1].patterns[FIRST_PATTERN]


class TestFingerprint:
    def test_fingerprint_stable_across_snapshot(
        self,
        project_controller: ProjectController,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        project_controller.add_sample(reconstruction_factory(), name="lead")

        original = fingerprint_project(project_controller.project, hashes=FreshHashes())
        snapshot = project_controller.project.snapshot()

        assert fingerprint_project(snapshot, hashes=FreshHashes()) == original

    def test_fingerprint_changes_with_state(
        self,
        project_controller: ProjectController,
    ) -> None:
        before = fingerprint_project(project_controller.project, hashes=FreshHashes())

        project_controller.set_tempo(project_controller.project.settings.tempo + 7)

        assert fingerprint_project(project_controller.project, hashes=FreshHashes()) != before


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
        for channel in project.song.channels.values():
            channel.patterns = dict(reversed(list(channel.patterns.items())))

        assert fresh_fingerprint(project) == baseline

    def test_two_patterns_swapping_indices_change_the_fingerprint(self) -> None:
        project = every_part_project()
        baseline = fresh_fingerprint(project)
        pool = project.song.channels[ChannelName.PULSE1].patterns

        pool[FIRST_PATTERN], pool[SECOND_PATTERN] = pool[SECOND_PATTERN], pool[FIRST_PATTERN]

        assert fresh_fingerprint(project) != baseline


class TestHashCache:
    """A value is hashed once per object, so a digest costs the values the gesture replaced."""

    def test_streams_hashed_once_per_reconstruction_object(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting: CountingHash[InstructionsItem] = CountingHash()
        cache = HashCache(stream_hash=counting)
        reconstruction = reconstruction_factory()

        first = cache.reconstruction(reconstruction)
        second = cache.reconstruction(reconstruction)

        assert first == second
        assert counting.calls == _streams(reconstruction)

    def test_the_memoized_digest_is_the_fresh_one(self, reconstruction_factory: ReconstructionFactory) -> None:
        reconstruction = reconstruction_factory()

        assert HashCache().reconstruction(reconstruction) == hash_reconstruction(reconstruction)

    def test_distinct_reconstructions_hash_independently(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting: CountingHash[InstructionsItem] = CountingHash()
        cache = HashCache(stream_hash=counting)
        first = reconstruction_factory()
        second = reconstruction_factory()

        cache.reconstruction(first)
        cache.reconstruction(second)

        assert counting.calls == _streams(first) + _streams(second)

    def test_an_edit_hashes_the_one_stream_it_replaced(self, reconstruction_factory: ReconstructionFactory) -> None:
        counting: CountingHash[InstructionsItem] = CountingHash()
        cache = HashCache(stream_hash=counting)
        reconstruction = reconstruction_factory()
        edited = _edited(reconstruction)
        cache.reconstruction(reconstruction)

        cache.reconstruction(edited)

        assert counting.calls == _streams(reconstruction) + [edited.streams[ChannelName.PULSE1]]
        assert cache.reconstruction(edited) == hash_reconstruction(edited)

    def test_prune_drops_hashes_for_discarded_reconstructions(
        self,
        project_controller: ProjectController,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        counting: CountingHash[InstructionsItem] = CountingHash()
        cache = HashCache(stream_hash=counting)
        kept = project_controller.add_sample(reconstruction_factory(), name="kept").reconstruction
        discarded = reconstruction_factory()
        cache.reconstruction(kept)
        cache.reconstruction(discarded)

        cache.prune([project_controller.project])

        cache.reconstruction(kept)
        cache.reconstruction(discarded)
        assert counting.calls == _streams(kept) + _streams(discarded) + _streams(discarded)

    def test_patterns_hashed_once_per_pattern_object(self) -> None:
        counting: CountingHash[Pattern] = CountingHash()
        cache = HashCache(pattern_hash=counting)
        song = every_part_project().song

        first = cache.song(song)
        second = cache.song(song)

        assert first == second
        assert counting.calls == _patterns(song)

    def test_the_memoized_song_digest_is_the_fresh_one(self) -> None:
        song = every_part_project().song

        assert HashCache().song(song) == hash_song(song)

    def test_a_row_edit_hashes_the_one_pattern_it_replaced(self) -> None:
        counting: CountingHash[Pattern] = CountingHash()
        cache = HashCache(pattern_hash=counting)
        song = every_part_project().song
        original = _patterns(song)
        cache.song(song)

        written = _edit_a_row(song)
        cache.song(song)

        assert counting.calls == original + [written]
        assert cache.song(song) == hash_song(song)

    def test_a_snapshot_shares_its_patterns_with_the_song_it_copies(self) -> None:
        counting: CountingHash[Pattern] = CountingHash()
        cache = HashCache(pattern_hash=counting)
        project = every_part_project()
        cache.song(project.song)

        assert cache.song(project.snapshot().song) == cache.song(project.song)
        assert counting.calls == _patterns(project.song)

    def test_prune_drops_hashes_for_discarded_patterns(self) -> None:
        counting: CountingHash[Pattern] = CountingHash()
        cache = HashCache(pattern_hash=counting)
        project = every_part_project()
        before = project.snapshot()
        replaced = project.song.channels[ChannelName.PULSE1].patterns[FIRST_PATTERN]
        cache.song(before.song)
        written = _edit_a_row(project.song)
        cache.song(project.song)

        cache.prune([project])

        cache.song(before.song)
        assert counting.calls == _patterns(before.song) + [written, replaced]


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

        with history.transaction(HistoryAction.EDIT_ROW):
            controller.set_row(ChannelName.PULSE1, FIRST_PATTERN, 0, volume=EDITED_ROW.volume)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        history.undo()
        history.undo()
        history.undo()
        history.redo()
        history.jump_to(3)

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

    def test_restore_raises_on_a_stream_mutated_in_place(
        self,
        history_factory: HistoryFactory,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A stream's digest is memoized by identity on capture and read afresh on verification."""
        controller, history = history_factory()
        with history.transaction(HistoryAction.ADD_SAMPLE):
            sample = controller.add_sample(reconstruction_factory(), name="lead")

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        stream = sample.reconstruction.instructions_data[0]
        object.__setattr__(stream, "initial_pitch", stream.initial_pitch + 1)

        with pytest.raises(HistoryIntegrityError):
            history.undo()

    def test_restore_raises_on_a_pattern_mutated_in_place(self, history_factory: HistoryFactory) -> None:
        """A pattern's digest is memoized by identity on capture and read afresh on verification."""
        controller, history = history_factory()
        with history.transaction(HistoryAction.EDIT_ROW):
            controller.set_row(ChannelName.PULSE1, FIRST_PATTERN, 0, volume=EDITED_ROW.volume)

        with history.transaction(HistoryAction.SET_TEMPO):
            controller.set_tempo(150)

        pattern = controller.project.song.channels[ChannelName.PULSE1].patterns[FIRST_PATTERN]
        object.__setattr__(pattern, "name", MUTATED_NAME)

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
        assert len(history._hash_cache._reconstructions) == 0
        assert len(history._hash_cache._streams) == 0
        assert len(history._hash_cache._assignments) == 0

    def test_eviction_prunes_cache_to_retained_patterns(self, history_factory: HistoryFactory) -> None:
        controller, history = history_factory(budget=2)
        for row_index in range(3):
            with history.transaction(HistoryAction.EDIT_ROW):
                controller.set_row(ChannelName.PULSE1, FIRST_PATTERN, row_index, volume=EDITED_ROW.volume)

        retained = [entry.project for entry in history.entries] + [controller.project]
        assert history._hash_cache is not None
        assert len(history._hash_cache._patterns) == len(_every_pattern(retained))
