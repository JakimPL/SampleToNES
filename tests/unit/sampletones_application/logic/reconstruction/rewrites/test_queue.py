from dataclasses import dataclass, field
from typing import Final, List, Optional, Tuple
from unittest.mock import MagicMock

import pytest

from sampletones_application.logic.reconstruction.edit import (
    ChannelEdit,
    ReconstructionEdit,
    Retune,
    StemRemoval,
)
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.logic.reconstruction.rewrites.queue import ReconstructionRewrites
from sampletones_application.logic.reconstruction.rewrites.steps import (
    AfterEdits,
    ChannelChange,
    RateChange,
    StemRemovalRequest,
)
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.features.envelope import Envelope
from sampletones_core.reconstructions import Reconstruction
from tests.conftest import ReconstructionFactory
from tests.suite.regeneration import HeldRegeneration
from tests.suite.stems import (
    SHARED_CHANNEL,
    SOLE_CHANNEL,
    STEM_A_ID,
    STEM_B_ID,
    taking_turns,
)

__all__ = ["taking_turns"]

VOICE_ID: Final[str] = "turns-id"
FIRST_VOLUME: Final[Envelope[int]] = Envelope[int](items=(5, 5))
SECOND_VOLUME: Final[Envelope[int]] = Envelope[int](items=(4, 4))
LATER_VOLUME: Final[Envelope[int]] = Envelope[int](items=(3, 3))
SOLE_VOLUME: Final[Envelope[int]] = Envelope[int](items=(2,))
ARPEGGIO: Final[Envelope[int]] = Envelope[int](items=(0, 3))
RETUNED_FREQUENCY: Final[int] = 50
LATER_FREQUENCY: Final[int] = 40


def _change(channel_name: ChannelName, feature_key: FeatureKey, envelope: Envelope[int]) -> ChannelChange:
    return ChannelChange(
        channel_name=channel_name,
        feature_key=feature_key,
        envelopes={feature_key: envelope},
        initial_pitch=None,
    )


def _removal(stem_id: int) -> StemRemovalRequest:
    return StemRemovalRequest(stem_id=stem_id, stem_name=str(stem_id))


@dataclass
class Outcome:
    """Everything the rewrites reported, in the order they reported it."""

    edits: List[ReconstructionEdit] = field(default_factory=list)
    dropped: int = 0
    failures: List[Exception] = field(default_factory=list)
    busy: List[bool] = field(default_factory=list)


@pytest.fixture
def regeneration() -> HeldRegeneration:
    return HeldRegeneration()


@pytest.fixture
def outcome() -> Outcome:
    return Outcome()


@pytest.fixture
def rewrites(
    reconstruction_manager: ReconstructionManager,
    regeneration: HeldRegeneration,
    outcome: Outcome,
    taking_turns: Reconstruction,
) -> ReconstructionRewrites:
    """The steps of the two-recording document, each landing edit adopted the way the coordinator adopts it."""
    reconstruction_manager.load_reconstruction_object(taking_turns, name="turns", voice_id=VOICE_ID)

    def adopt(edit: ReconstructionEdit) -> None:
        outcome.edits.append(edit)
        reconstruction_manager.apply_edited(edit.reconstruction)

    def drop() -> None:
        outcome.dropped += 1

    rewrites = ReconstructionRewrites(reconstruction_manager, regeneration)
    rewrites.on_edit = adopt
    rewrites.on_dropped = drop
    rewrites.on_failed = outcome.failures.append
    rewrites.on_busy_changed = outcome.busy.append
    return rewrites


def _volume_items(reconstruction: Optional[Reconstruction], channel_name: ChannelName) -> Tuple[int, ...]:
    """The volumes of the frames a channel sounds."""
    assert reconstruction is not None
    return tuple(instruction.volume for instruction in reconstruction.instructions[channel_name] if instruction.on)


class TestMergingWhatWaits:
    """A change joins the one waiting at the end of the line when both move the same channel, and nothing else."""

    def test_changes_of_one_channel_waiting_together_rebuild_once(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, SECOND_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.ARPEGGIO, ARPEGGIO))
        regeneration.finish()

        (merged,) = regeneration.held
        assert merged.features.volume == SECOND_VOLUME
        assert merged.features.arpeggio == ARPEGGIO

    def test_nothing_merges_into_the_running_rebuild(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, SECOND_VOLUME))

        (running,) = regeneration.held
        assert running.features.volume == FIRST_VOLUME
        regeneration.finish()
        assert regeneration.held[0].features.volume == SECOND_VOLUME

    def test_nothing_merges_across_another_channel(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, SECOND_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, LATER_VOLUME))

        rebuilt: List[Tuple[ChannelName, Envelope[int]]] = []
        while regeneration.held:
            rebuilt.append((regeneration.held[0].channel_name, regeneration.held[0].features.volume))
            regeneration.finish()

        assert rebuilt == [
            (SHARED_CHANNEL, FIRST_VOLUME),
            (SHARED_CHANNEL, SECOND_VOLUME),
            (SOLE_CHANNEL, SOLE_VOLUME),
            (SHARED_CHANNEL, LATER_VOLUME),
        ]

    def test_a_later_rate_replaces_one_waiting(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(RateChange(nes_frequency=RETUNED_FREQUENCY))
        rewrites.request(RateChange(nes_frequency=LATER_FREQUENCY))
        regeneration.finish()

        retunes = [edit for edit in outcome.edits if isinstance(edit, Retune)]
        assert [retune.nes_frequency for retune in retunes] == [LATER_FREQUENCY]


class TestEachStepReadsTheDocumentAtItsTurn:
    """A step is built from the document the step before it left, and from the listening as it stands."""

    def test_a_rebuild_starts_from_what_the_step_before_it_left(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        regeneration.finish()

        (second,) = regeneration.held
        assert second.reconstruction is reconstruction_manager.reconstruction
        assert _volume_items(second.reconstruction, SHARED_CHANNEL) == FIRST_VOLUME.items

    def test_the_dimensions_a_change_leaves_are_read_from_the_document(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.ARPEGGIO, ARPEGGIO))
        regeneration.finish()

        (arpeggio,) = regeneration.held
        assert arpeggio.features.volume.items[: len(FIRST_VOLUME.items)] == FIRST_VOLUME.items

    def test_the_recordings_heard_are_read_at_the_changes_turn(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        reconstruction_manager.listening.set_channels(STEM_B_ID, frozenset({SOLE_CHANNEL}))
        regeneration.finish()

        (shared,) = regeneration.held
        assert shared.heard == frozenset({STEM_A_ID})


class TestAStepThatNoLongerApplies:
    """A removal or a rate the document already carries is let go at its turn."""

    def test_a_recording_a_step_before_took_out_is_skipped(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_removal(STEM_B_ID))
        rewrites.request(_removal(STEM_B_ID))
        regeneration.finish()

        assert [type(edit) for edit in outcome.edits] == [ChannelEdit, StemRemoval]

    def test_the_last_recording_is_skipped(
        self,
        rewrites: ReconstructionRewrites,
        outcome: Outcome,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_removal(STEM_B_ID))
        rewrites.request(_removal(STEM_A_ID))

        assert [type(edit) for edit in outcome.edits] == [StemRemoval]
        reconstruction = reconstruction_manager.reconstruction
        assert reconstruction is not None
        assert list(reconstruction.stems_data.config.entries_by_id) == [STEM_A_ID]

    def test_a_rate_the_document_runs_at_is_skipped(
        self,
        rewrites: ReconstructionRewrites,
        outcome: Outcome,
        taking_turns: Reconstruction,
    ) -> None:
        rewrites.request(RateChange(nes_frequency=taking_turns.config.nes_frequency))

        assert outcome.edits == []

    def test_another_rate_retunes_the_document(
        self,
        rewrites: ReconstructionRewrites,
        outcome: Outcome,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(RateChange(nes_frequency=RETUNED_FREQUENCY))

        (retune,) = outcome.edits
        assert isinstance(retune, Retune)
        assert retune.nes_frequency == RETUNED_FREQUENCY
        assert retune.reconstruction.config.nes_frequency == RETUNED_FREQUENCY

    def test_a_change_with_no_document_open_is_let_go(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
        outcome: Outcome,
    ) -> None:
        reconstruction_manager.close_reconstruction()

        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_removal(STEM_B_ID))
        rewrites.request(RateChange(nes_frequency=RETUNED_FREQUENCY))

        assert regeneration.held == ()
        assert outcome.edits == []
        assert not rewrites.is_busy


class TestAResultLandsOnItsOwnDocument:
    """A rebuild's result lands only on the document it was computed from."""

    def test_a_result_for_the_open_document_lands(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        regeneration.finish()

        (edit,) = outcome.edits
        assert isinstance(edit, ChannelEdit)
        assert (edit.channel_name, edit.feature_key) == (SHARED_CHANNEL, FeatureKey.VOLUME)

    def test_a_result_for_a_document_put_away_is_dropped_and_the_panel_redrawn(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
        outcome: Outcome,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        reconstruction_manager.load_reconstruction_object(reconstruction_factory(), name="other", voice_id="other")
        regeneration.finish()

        assert outcome.edits == []
        assert outcome.dropped == 1

    def test_a_failed_rebuild_is_reported_and_the_next_step_runs(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        failure = RuntimeError("synthesis failed")
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))

        regeneration.fail(failure)

        assert outcome.failures == [failure]
        assert outcome.dropped == 1
        assert regeneration.held[0].channel_name is SOLE_CHANNEL

    def test_a_result_with_no_rebuild_running_is_refused(
        self,
        rewrites: ReconstructionRewrites,
        taking_turns: Reconstruction,
    ) -> None:
        stray = HeldRegeneration()
        stray.subscribe(rewrites._on_result)
        stray.start(taking_turns, SHARED_CHANNEL, taking_turns.export()[SHARED_CHANNEL], frozenset())

        with pytest.raises(RuntimeError, match="no rebuild was running"):
            stray.finish()


class TestDroppingTheLine:
    """An outside replacement lets the edits meant for the document it puts away go."""

    def test_the_waiting_edits_leave_and_the_running_result_lands_nowhere(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        rewrites.request(RateChange(nes_frequency=RETUNED_FREQUENCY))

        rewrites.drop()
        regeneration.finish()

        assert outcome.edits == []
        assert outcome.dropped == 0
        assert regeneration.held == ()
        assert not rewrites.is_busy

    def test_a_waiting_gesture_keeps_its_place(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        """A save or an undo the reader asked for still happens, on the document now open."""
        gesture = MagicMock()
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(AfterEdits(gesture=gesture))

        rewrites.drop()
        gesture.assert_not_called()
        regeneration.finish()

        gesture.assert_called_once_with()


class TestThePanelDrawsWhatTheDocumentWillHold:
    """The changes on their way are written over the document's envelopes, in the order they were made."""

    def test_the_running_and_the_waiting_changes_are_drawn(
        self,
        rewrites: ReconstructionRewrites,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        document = reconstruction_manager.current_features
        assert document is not None

        drawn = rewrites.drawn(document)

        assert drawn[SHARED_CHANNEL].volume == FIRST_VOLUME
        assert drawn[SOLE_CHANNEL].volume == SOLE_VOLUME
        assert drawn.ownership == document.ownership

    def test_a_later_change_of_a_dimension_is_drawn_over_an_earlier_one(
        self,
        rewrites: ReconstructionRewrites,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, LATER_VOLUME))
        document = reconstruction_manager.current_features
        assert document is not None

        assert rewrites.drawn(document)[SHARED_CHANNEL].volume == LATER_VOLUME

    def test_the_drawing_leaves_the_line_as_it_stands(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        document = reconstruction_manager.current_features
        assert document is not None

        rewrites.drawn(document)

        assert len(regeneration.held) == 1
        assert rewrites.is_busy

    def test_a_document_put_away_draws_nothing_of_its_rebuild(
        self,
        rewrites: ReconstructionRewrites,
        reconstruction_manager: ReconstructionManager,
        taking_turns: Reconstruction,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        reconstruction_manager.load_reconstruction_object(taking_turns.model_copy(), name="copy", voice_id="copy")
        document = reconstruction_manager.current_features
        assert document is not None

        assert rewrites.drawn(document) == document

    def test_nothing_on_its_way_draws_the_document(
        self,
        rewrites: ReconstructionRewrites,
        reconstruction_manager: ReconstructionManager,
    ) -> None:
        document = reconstruction_manager.current_features
        assert document is not None

        assert rewrites.drawn(document) is document


class TestAStepThatReshapesTheDocument:
    """A change drawn while a removal or a whole-document gesture waits is refused, and the panel redrawn once the line empties."""

    @pytest.mark.parametrize("reshaping", ("removal", "gesture"))
    def test_the_change_is_refused(
        self,
        reshaping: str,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_removal(STEM_B_ID) if reshaping == "removal" else AfterEdits(gesture=MagicMock()))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        regeneration.finish()

        assert regeneration.held == ()

    @pytest.mark.parametrize("reshaping", ("removal", "gesture"))
    def test_the_panel_is_redrawn_once_the_line_empties(
        self,
        reshaping: str,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_removal(STEM_B_ID) if reshaping == "removal" else AfterEdits(gesture=MagicMock()))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        assert outcome.dropped == 0

        regeneration.finish()

        assert outcome.dropped == 1

    def test_a_change_after_the_step_has_run_is_taken(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_removal(STEM_B_ID))
        regeneration.finish()

        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, LATER_VOLUME))

        assert len(regeneration.held) == 1


class TestTheBusySpan:
    """The line reports filling as the first step waits or runs, and emptying once the last one lands."""

    def test_a_rebuild_fills_the_line_until_it_lands(
        self,
        rewrites: ReconstructionRewrites,
        regeneration: HeldRegeneration,
        outcome: Outcome,
    ) -> None:
        rewrites.request(_change(SHARED_CHANNEL, FeatureKey.VOLUME, FIRST_VOLUME))
        rewrites.request(_change(SOLE_CHANNEL, FeatureKey.VOLUME, SOLE_VOLUME))
        assert rewrites.is_busy
        regeneration.finish()
        assert outcome.busy == [True]

        regeneration.finish()

        assert outcome.busy == [True, False]
        assert not rewrites.is_busy

    def test_steps_taken_at_once_leave_the_line_empty(
        self,
        rewrites: ReconstructionRewrites,
        outcome: Outcome,
    ) -> None:
        gesture = MagicMock()

        rewrites.request(_removal(STEM_B_ID))
        rewrites.request(AfterEdits(gesture=gesture))

        gesture.assert_called_once_with()
        assert outcome.busy == []
