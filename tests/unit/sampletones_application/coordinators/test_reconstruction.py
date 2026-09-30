from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.layout.behavior.scheduling.scheduling import SchedulingBehavior
from sampletones_application.logic.history.action import HistoryAction
from sampletones_application.logic.history.manager import HistoryManager
from sampletones_application.logic.project.controller import ProjectController
from sampletones_application.logic.project.manager import ProjectManager
from sampletones_application.logic.reconstruction.edit import ChannelEdit, ReconstructionEdit, StemRemoval
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.services.regeneration.service import RegeneratedInstrument
from sampletones_application.services.result import ServiceSuccess
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.project.voices.creation import new_instrument
from sampletones_core.project.voices.sample import Sample
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import (
    InvalidMetadataError,
    InvalidReconstructionValuesError,
)
from sampletones_shared.paths.extensions import EXT_FILE_PROJECT
from tests.conftest import ReconstructionFactory
from tests.suite.application import HeldQueue, held_queue, scheduling
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.language import FakeLanguageManager

__all__ = ["held_queue", "scheduling"]

OPEN_VOICE_ID: Final[str] = "lead-id"
HISTORY_BUDGET: Final[int] = 16


class VoiceKind(Enum):
    SAMPLE = "sample"
    INSTRUMENT = "instrument"


@pytest.fixture
def reconstruction_coordinator() -> ReconstructionCoordinator:
    return ReconstructionCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
    )


def _gating_coordinator(
    *,
    unsaved: bool,
    embedded: bool,
) -> ReconstructionCoordinator:
    coordinator = ReconstructionCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
    )
    coordinator._reconstruction_manager.session.unsaved_changes = unsaved
    coordinator._reconstruction_manager.is_project_sample = embedded
    coordinator.set_reconstructions_tab(MagicMock())
    return coordinator


class TestReconstructionRestoreSuccess:
    def test_loads_and_keeps_session_pointer(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        path = Path("lead.stn")

        reconstruction_coordinator.load_reconstruction_safely(path)

        reconstruction_coordinator._reconstruction_manager.load_reconstruction.assert_called_once_with(path)
        reconstruction_coordinator._session_manager.set_current_reconstruction.assert_not_called()


class TestReconstructionRestoreAbsorbsFailures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        failure: Exception

    test_cases = (
        TestCase(
            label="invalid_values",
            failure=InvalidReconstructionValuesError("bad", ValueError("inner")),
            expected=None,
        ),
        TestCase(
            label="foreign_metadata",
            failure=InvalidMetadataError("foreign"),
            expected=None,
        ),
        TestCase(
            label="missing_file",
            failure=FileNotFoundError("gone"),
            expected=None,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_restore_clears_session_pointer(
        self,
        test_case: TestCase,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        reconstruction_coordinator._reconstruction_manager.load_reconstruction.side_effect = test_case.failure

        reconstruction_coordinator.load_reconstruction_safely(Path("lead.stn"))

        reconstruction_coordinator._session_manager.set_current_reconstruction.assert_called_once_with(
            test_case.expected
        )


class TestRegenerationApplyOrdering:
    def test_history_hook_sees_prior_reconstruction_identity(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """Pins the hook-before-apply order in ``apply_edit``.

        The hook records the edit against the project, so the history holds it by the time
        the open document rebinds to the regenerated object and the tab shows it.
        """
        manager = ReconstructionManager(scheduling=MagicMock())
        prior = reconstruction_factory()
        manager.load_reconstruction_object(prior, name="lead", voice_id=OPEN_VOICE_ID)
        observed: List[Optional[Reconstruction]] = []
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=lambda _outcome: observed.append(manager.reconstruction),
        )
        coordinator.set_reconstructions_tab(MagicMock())
        regenerated = reconstruction_factory()
        outcome = RegeneratedInstrument(
            reconstruction=regenerated,
            channel_name=ChannelName.PULSE1,
            feature_key=FeatureKey.VOLUME,
        )

        coordinator._on_regeneration_result(ServiceSuccess(value=outcome))

        assert len(observed) == 1
        assert observed[0] is prior
        assert manager.reconstruction is regenerated


class TestStemRemovalApplyOrdering:
    def test_a_removed_recording_travels_the_same_path_as_a_regenerated_instrument(
        self,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """Every edit of the open document is applied alike, so the history sees them alike."""
        manager = ReconstructionManager(scheduling=MagicMock())
        prior = reconstruction_factory()
        manager.load_reconstruction_object(prior, name="lead", voice_id=OPEN_VOICE_ID)
        observed: List[Optional[Reconstruction]] = []
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=lambda _edit: observed.append(manager.reconstruction),
        )
        coordinator.set_reconstructions_tab(MagicMock())
        remaining = reconstruction_factory()

        coordinator.apply_edit(StemRemoval(reconstruction=remaining, stem_name="kick"))

        assert observed == [prior]
        assert manager.reconstruction is remaining


class TestAnEditRedrawsWhatItRewrote:
    """The instruments panel keeps what its own edit drew, and draws afresh what a removal rewrote."""

    @pytest.fixture
    def tab(self, reconstruction_coordinator: ReconstructionCoordinator) -> MagicMock:
        tab = MagicMock(spec=ReconstructionTabCoordinator)
        reconstruction_coordinator.set_reconstructions_tab(tab)
        return tab

    def test_a_regenerated_instrument_keeps_the_envelopes_the_panel_draws(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """The regeneration carries what the reader typed, so a field being typed in keeps its text."""
        outcome = RegeneratedInstrument(
            reconstruction=reconstruction_factory(),
            channel_name=ChannelName.PULSE1,
            feature_key=FeatureKey.VOLUME,
        )

        reconstruction_coordinator._on_regeneration_result(ServiceSuccess(value=outcome))

        tab.update_reconstruction.assert_called_once_with()
        tab.redraw_reconstruction.assert_not_called()

    def test_a_removed_recording_redraws_the_instruments_panel(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A removal releases frames the panel drew as sounding, so the panel draws the document it leaves."""
        reconstruction_coordinator.apply_edit(
            StemRemoval(
                reconstruction=reconstruction_factory(),
                stem_name="kick",
            )
        )

        tab.redraw_reconstruction.assert_called_once_with(refit_waveform=False)
        tab.update_reconstruction.assert_not_called()


class TestReconstructionRestorePropagatesUnexpected:
    def test_runtime_error_propagates(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        reconstruction_coordinator._reconstruction_manager.load_reconstruction.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            reconstruction_coordinator.load_reconstruction_safely(Path("lead.stn"))

        reconstruction_coordinator._session_manager.set_current_reconstruction.assert_not_called()


class TestSaveConfirmationGating(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        unsaved: bool
        embedded: bool
        expects_prompt: bool

    test_cases = (
        TestCase(
            label="standalone_unsaved_prompts",
            unsaved=True,
            embedded=False,
            expects_prompt=True,
            expected=True,
        ),
        TestCase(
            label="embedded_unsaved_skips_prompt",
            unsaved=True,
            embedded=True,
            expects_prompt=False,
            expected=False,
        ),
        TestCase(
            label="standalone_saved_skips_prompt",
            unsaved=False,
            embedded=False,
            expects_prompt=False,
            expected=False,
        ),
        TestCase(
            label="embedded_saved_skips_prompt",
            unsaved=False,
            embedded=True,
            expects_prompt=False,
            expected=False,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_close_prompts_only_for_standalone_unsaved(
        self,
        test_case: TestCase,
    ) -> None:
        coordinator = _gating_coordinator(
            unsaved=test_case.unsaved,
            embedded=test_case.embedded,
        )

        coordinator.close_with_confirmation()

        if test_case.expects_prompt:
            coordinator._dialogs.show_save_confirmation.assert_called_once()
            coordinator._reconstruction_manager.close_reconstruction.assert_not_called()
        else:
            coordinator._dialogs.show_save_confirmation.assert_not_called()
            coordinator._reconstruction_manager.close_reconstruction.assert_called_once()

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_load_prompts_only_for_standalone_unsaved(
        self,
        test_case: TestCase,
    ) -> None:
        coordinator = _gating_coordinator(
            unsaved=test_case.unsaved,
            embedded=test_case.embedded,
        )
        path = Path("lead.stn")

        coordinator.load_with_confirmation(path)

        if test_case.expects_prompt:
            coordinator._dialogs.show_save_confirmation.assert_called_once()
            coordinator._reconstructions_tab.load_reconstruction.assert_not_called()
        else:
            coordinator._dialogs.show_save_confirmation.assert_not_called()
            coordinator._reconstructions_tab.load_reconstruction.assert_called_once_with(path)


@pytest.fixture
def project_manager() -> ProjectManager:
    return ProjectManager()


@pytest.fixture
def project_controller(project_manager: ProjectManager) -> ProjectController:
    return ProjectController(project_manager)


@pytest.fixture
def history(project_controller: ProjectController) -> HistoryManager:
    """A strict history, so an edit that reaches the project outside a transaction is reported."""
    history = HistoryManager(project_controller, budget=HISTORY_BUDGET, strict=True)
    project_controller.on_mutation = history.handle_mutation
    project_controller.on_saved = history.mark_saved
    return history


@pytest.fixture
def reconstruction_manager(scheduling: SchedulingBehavior) -> ReconstructionManager:
    return ReconstructionManager(scheduling=scheduling)


@pytest.fixture
def tab() -> MagicMock:
    return MagicMock(spec=ReconstructionTabCoordinator)


@pytest.fixture
def following_coordinator(
    reconstruction_manager: ReconstructionManager,
    project_manager: ProjectManager,
    project_controller: ProjectController,
    history: HistoryManager,
    tab: MagicMock,
    held_queue: HeldQueue,
) -> ReconstructionCoordinator:
    """The coordinator on a real project, history and document, wired the way the application wires it.

    The application writes an edit of a project sample back into the project as one history entry,
    follows every project state change, and fans a replaced project out to the sequencer, which
    reseeds the history, before the coordinator follows it. The fixture repeats that wiring, and a
    new project stands open.
    """

    def write_back(edit: ReconstructionEdit) -> None:
        voice_id = reconstruction_manager.voice_id
        if voice_id is None:
            return

        with history.transaction(
            HistoryAction.EDIT_RECONSTRUCTION,
            coalesce=edit.coalesce_key(voice_id),
        ):
            project_controller.replace_sample_reconstruction(voice_id, edit.reconstruction)

    coordinator = ReconstructionCoordinator(
        reconstruction_manager,
        MagicMock(),
        MagicMock(),
        MagicMock(),
        project_controller,
        history,
        dialogs=MagicMock(),
        language_manager=FakeLanguageManager({}),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=write_back,
    )
    coordinator.set_reconstructions_tab(tab)

    def realign() -> None:
        history.reset()
        coordinator.follow_replaced_project()

    project_manager.session.on_state_changed = coordinator.follow_project
    project_controller.on_project_replaced = realign
    project_controller.new()
    return coordinator


@pytest.fixture
def open_sample(
    following_coordinator: ReconstructionCoordinator,
    project_controller: ProjectController,
    history: HistoryManager,
    tab: MagicMock,
    held_queue: HeldQueue,
    reconstruction_factory: ReconstructionFactory,
) -> Sample:
    """A sample added to the project and opened on the tab, with the calls opening it cleared."""
    with history.transaction(HistoryAction.ADD_SAMPLE):
        sample = project_controller.add_sample(reconstruction_factory(), "lead")
    following_coordinator.open_project_voice(sample.id)
    held_queue.drain()
    tab.reset_mock()
    return sample


@pytest.fixture
def standalone_path(
    reconstruction_manager: ReconstructionManager,
    reconstruction_factory: ReconstructionFactory,
    tmp_path: Path,
) -> Path:
    """A reconstruction file opened on the tab, standing apart from the project."""
    path = tmp_path / "lead.stn"
    reconstruction_factory().save(path)
    reconstruction_manager.load_reconstruction(path)
    return path


def _retimed(reconstruction: Reconstruction) -> Reconstruction:
    """The same reconstruction timed at another NES frequency, which spans another length."""
    return reconstruction.model_copy(
        update={"config": reconstruction.config.with_library(nes_frequency=reconstruction.config.nes_frequency // 2)}
    )


class TestTheTabFollowsTheVoiceItShows:
    """The tab knows the voice it shows by its id, so a restore reaches it and a replaced project lets it go."""

    def test_an_undo_keeping_the_sample_shows_the_reconstruction_it_restores(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        history: HistoryManager,
        open_sample: Sample,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        original = open_sample.reconstruction
        following_coordinator.apply_edit(
            ChannelEdit(
                reconstruction=reconstruction_factory(),
                channel_name=ChannelName.PULSE1,
                feature_key=FeatureKey.VOLUME,
            )
        )
        tab.reset_mock()

        history.undo()

        assert reconstruction_manager.reconstruction is original
        assert reconstruction_manager.voice_id == open_sample.id
        tab.redraw_reconstruction.assert_called_once_with(refit_waveform=False)

    def test_an_undo_across_a_rate_change_refits_the_waveform(
        self,
        following_coordinator: ReconstructionCoordinator,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
        tab: MagicMock,
    ) -> None:
        retimed = _retimed(open_sample.reconstruction)
        with history.transaction(HistoryAction.SET_NES_FREQUENCY):
            project_controller.replace_sample_reconstruction(open_sample.id, retimed)
        following_coordinator.retune_sample(open_sample.id, retimed)
        tab.reset_mock()

        history.undo()

        tab.redraw_reconstruction.assert_called_once_with(refit_waveform=True)

    def test_an_undo_leaving_the_reconstruction_as_it_was_redraws_nothing(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
        tab: MagicMock,
    ) -> None:
        """A restore shares every reconstruction it kept, so the document it already shows stands."""
        with history.transaction(HistoryAction.SET_TEMPO):
            project_controller.set_tempo(150)
        tab.reset_mock()

        history.undo()

        assert reconstruction_manager.reconstruction is open_sample.reconstruction
        tab.redraw_reconstruction.assert_not_called()
        tab.update_reconstruction.assert_not_called()

    def test_an_undo_taking_the_sample_out_closes_it(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        history: HistoryManager,
        open_sample: Sample,
    ) -> None:
        history.undo()

        assert reconstruction_manager.current_reconstruction is None
        assert reconstruction_manager.voice_id is None

    def test_a_redo_bringing_the_sample_back_leaves_the_tab_empty(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
    ) -> None:
        """A voice that comes back is the reader's to open again."""
        history.undo()

        history.redo()

        assert project_controller.project.voice(open_sample.id) is not None
        assert reconstruction_manager.current_reconstruction is None

    def test_a_redo_taking_the_sample_out_closes_it(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
    ) -> None:
        with history.transaction(HistoryAction.REMOVE_VOICE):
            project_controller.remove_voice(open_sample.id)
        history.undo()
        following_coordinator.open_project_voice(open_sample.id)

        history.redo()

        assert reconstruction_manager.current_reconstruction is None

    def test_removing_the_sample_closes_it(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
    ) -> None:
        with history.transaction(HistoryAction.REMOVE_VOICE):
            project_controller.remove_voice(open_sample.id)

        assert reconstruction_manager.current_reconstruction is None

    def test_an_edit_writing_the_project_first_leaves_the_document_to_the_edit(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        open_sample: Sample,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """The write-back stamps the project while the document still holds what the edit started from."""
        edited = reconstruction_factory()

        following_coordinator.apply_edit(
            ChannelEdit(
                reconstruction=edited,
                channel_name=ChannelName.PULSE1,
                feature_key=FeatureKey.VOLUME,
            )
        )

        assert reconstruction_manager.reconstruction is edited
        tab.redraw_reconstruction.assert_not_called()
        tab.update_reconstruction.assert_called_once_with()

    def test_a_new_project_lets_the_sample_go(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        open_sample: Sample,
    ) -> None:
        project_controller.new()

        assert reconstruction_manager.current_reconstruction is None

    def test_closing_the_project_lets_the_sample_go(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        open_sample: Sample,
    ) -> None:
        project_controller.close()

        assert reconstruction_manager.current_reconstruction is None

    def test_reopening_the_saved_project_lets_the_sample_go(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        open_sample: Sample,
        tmp_path: Path,
    ) -> None:
        """The file keeps each voice's id, so the reopened project names the voice the tab showed."""
        path = tmp_path / f"song{EXT_FILE_PROJECT}"
        project_controller.save(path)

        project_controller.load(path)

        assert isinstance(project_controller.project.voice(open_sample.id), Sample)
        assert reconstruction_manager.current_reconstruction is None

    def test_a_standalone_document_outlasts_a_new_and_a_closed_project(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        standalone_path: Path,
    ) -> None:
        project_controller.new()
        project_controller.close()

        assert reconstruction_manager.filepath == standalone_path

    def test_a_restore_asks_the_instrument_to_follow_as_restored(
        self,
        following_coordinator: ReconstructionCoordinator,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
    ) -> None:
        with history.transaction(HistoryAction.SET_TEMPO):
            project_controller.set_tempo(150)
        tab.reset_mock()

        history.undo()

        tab.follow_instrument.assert_called_with(restored=True)

    def test_an_edit_asks_the_instrument_to_follow_as_it_stands(
        self,
        following_coordinator: ReconstructionCoordinator,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
    ) -> None:
        tab.reset_mock()

        with history.transaction(HistoryAction.SET_TEMPO):
            project_controller.set_tempo(150)

        tab.follow_instrument.assert_called_once_with(restored=False)

    def test_a_replaced_project_closes_the_instrument(
        self,
        following_coordinator: ReconstructionCoordinator,
        project_controller: ProjectController,
        tab: MagicMock,
    ) -> None:
        tab.reset_mock()

        project_controller.close()

        tab.close_instrument.assert_called_once_with()


class TestOpeningAProjectVoice(BaseTestSuite):
    """Edit on a voice puts it in front of the tab, asking first where that would lose unsaved work."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        kind: VoiceKind

    test_cases = (
        TestCase(label="sample", kind=VoiceKind.SAMPLE),
        TestCase(label="instrument", kind=VoiceKind.INSTRUMENT),
    )

    @staticmethod
    def _add_voice(
        kind: VoiceKind,
        project_controller: ProjectController,
        history: HistoryManager,
        reconstruction_factory: ReconstructionFactory,
    ) -> str:
        match kind:
            case VoiceKind.SAMPLE:
                with history.transaction(HistoryAction.ADD_SAMPLE):
                    return project_controller.add_sample(reconstruction_factory(), "lead").id
            case VoiceKind.INSTRUMENT:
                with history.transaction(HistoryAction.ADD_INSTRUMENT):
                    return project_controller.add_instrument(new_instrument("lead")).id

    def test_a_sample_opens_as_the_document_it_is(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        voice_id = self._add_voice(VoiceKind.SAMPLE, project_controller, history, reconstruction_factory)
        sample = project_controller.project.voice(voice_id)
        assert isinstance(sample, Sample)

        following_coordinator.open_project_voice(voice_id)

        assert reconstruction_manager.voice_id == voice_id
        assert reconstruction_manager.reconstruction is sample.reconstruction
        tab.release_instrument.assert_called_once_with()

    def test_an_instrument_opens_in_the_editor_on_its_tab(
        self,
        following_coordinator: ReconstructionCoordinator,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        voice_id = self._add_voice(VoiceKind.INSTRUMENT, project_controller, history, reconstruction_factory)

        following_coordinator.open_project_voice(voice_id)

        tab.edit_instrument.assert_called_once_with(voice_id)
        following_coordinator._on_tab_switch.assert_called_once_with(Tab.RECONSTRUCTIONS)

    def test_an_unknown_voice_opens_nothing(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        tab: MagicMock,
    ) -> None:
        following_coordinator.open_project_voice("gone")

        assert reconstruction_manager.current_reconstruction is None
        tab.edit_instrument.assert_not_called()

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_an_unsaved_standalone_document_is_offered_a_save_first(
        self,
        test_case: TestCase,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
        standalone_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        voice_id = self._add_voice(test_case.kind, project_controller, history, reconstruction_factory)
        reconstruction_manager.mark_updated()

        following_coordinator.open_project_voice(voice_id)

        following_coordinator._dialogs.show_save_confirmation.assert_called_once()
        assert reconstruction_manager.filepath == standalone_path
        tab.edit_instrument.assert_not_called()

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_answer_opens_the_voice(
        self,
        test_case: TestCase,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        tab: MagicMock,
        standalone_path: Path,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        voice_id = self._add_voice(test_case.kind, project_controller, history, reconstruction_factory)
        reconstruction_manager.mark_updated()
        following_coordinator.open_project_voice(voice_id)

        following_coordinator._dialogs.show_save_confirmation.call_args.kwargs["on_confirm"]()

        match test_case.kind:
            case VoiceKind.SAMPLE:
                assert reconstruction_manager.voice_id == voice_id
            case VoiceKind.INSTRUMENT:
                tab.edit_instrument.assert_called_once_with(voice_id)

    def test_an_edited_project_sample_opens_another_voice_at_once(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        project_controller: ProjectController,
        history: HistoryManager,
        open_sample: Sample,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        """A project sample's edits belong to the project, so putting it away loses nothing."""
        voice_id = self._add_voice(VoiceKind.SAMPLE, project_controller, history, reconstruction_factory)
        reconstruction_manager.mark_updated()

        following_coordinator.open_project_voice(voice_id)

        following_coordinator._dialogs.show_save_confirmation.assert_not_called()
        assert reconstruction_manager.voice_id == voice_id


class TestAnOutsideRewriteOfTheOpenSample:
    """A sample replaced or retuned from the sequencer shows on the tab only where the tab has it open."""

    def test_a_replaced_sample_shows_its_new_reconstruction(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        open_sample: Sample,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        incoming = reconstruction_factory()

        following_coordinator.replace_sample(open_sample.id, incoming)

        assert reconstruction_manager.reconstruction is incoming
        tab.redraw_reconstruction.assert_called_once_with(refit_waveform=False)

    def test_a_replacement_at_another_rate_refits_the_waveform(
        self,
        following_coordinator: ReconstructionCoordinator,
        open_sample: Sample,
        tab: MagicMock,
    ) -> None:
        following_coordinator.replace_sample(open_sample.id, _retimed(open_sample.reconstruction))

        tab.redraw_reconstruction.assert_called_once_with(refit_waveform=True)

    def test_a_replaced_sample_the_tab_holds_no_longer_leaves_the_document_alone(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        open_sample: Sample,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        following_coordinator.replace_sample("another-id", reconstruction_factory())

        assert reconstruction_manager.reconstruction is open_sample.reconstruction
        tab.redraw_reconstruction.assert_not_called()

    def test_a_replacement_with_nothing_open_opens_nothing(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        following_coordinator.replace_sample(OPEN_VOICE_ID, reconstruction_factory())

        assert reconstruction_manager.current_reconstruction is None
        tab.redraw_reconstruction.assert_not_called()

    def test_a_retuned_sample_shows_its_new_length(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        open_sample: Sample,
        tab: MagicMock,
    ) -> None:
        """A retune carries every envelope over, so the panel keeps what it draws."""
        retimed = _retimed(open_sample.reconstruction)

        following_coordinator.retune_sample(open_sample.id, retimed)

        assert reconstruction_manager.reconstruction is retimed
        tab.update_reconstruction.assert_called_once_with(refit_waveform=True)
        tab.redraw_reconstruction.assert_not_called()

    def test_another_sample_s_retune_leaves_the_document_alone(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        open_sample: Sample,
        tab: MagicMock,
    ) -> None:
        following_coordinator.retune_sample("another-id", _retimed(open_sample.reconstruction))

        assert reconstruction_manager.reconstruction is open_sample.reconstruction
        tab.update_reconstruction.assert_not_called()

    def test_a_retune_with_nothing_open_opens_nothing(
        self,
        following_coordinator: ReconstructionCoordinator,
        reconstruction_manager: ReconstructionManager,
        tab: MagicMock,
        reconstruction_factory: ReconstructionFactory,
    ) -> None:
        following_coordinator.retune_sample(OPEN_VOICE_ID, reconstruction_factory())

        assert reconstruction_manager.current_reconstruction is None
        tab.update_reconstruction.assert_not_called()


class TestTheSaveAPromptWaitsOn:
    """A save prompt goes on, asks again or stands aside according to what the save came to."""

    def test_a_document_with_a_file_is_written(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        reconstruction_coordinator._reconstruction_manager.save_reconstruction.return_value = True

        assert reconstruction_coordinator.save() is SaveOutcome.WRITTEN

    def test_a_document_with_nothing_to_write_to_calls_the_save_off(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        reconstruction_coordinator._reconstruction_manager.save_reconstruction.return_value = False

        assert reconstruction_coordinator.save() is SaveOutcome.CALLED_OFF

    def test_a_write_that_fails_shows_its_error(
        self,
        reconstruction_coordinator: ReconstructionCoordinator,
    ) -> None:
        failure = OSError("disk full")
        reconstruction_coordinator._reconstruction_manager.save_reconstruction.side_effect = failure

        assert reconstruction_coordinator.save() is SaveOutcome.FAILED
        assert reconstruction_coordinator._dialogs.show_error.call_args.args[0] is failure


NO_PROMPT: Final[str] = "none"
SAVE_PROMPT: Final[str] = "save"
REPLACED_PROMPT: Final[str] = "replaced"
REPLACED_MESSAGE_KEY: Final[str] = "global.dialog.message.load_replaced_reconstruction"
DISCARD_LABEL_KEY: Final[str] = "global.dialog.label.discard"


class TestLoadingAConversion(BaseTestSuite):
    """Loading what a conversion wrote asks first about unsaved changes. A conversion that wrote over
    the open document's own file offers to discard the changes or keep them, since a save would write
    the old document over the new one."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        unsaved: bool
        embedded: bool
        same_file: bool

    test_cases = (
        TestCase(label="saved_another_file", unsaved=False, embedded=False, same_file=False, expected=NO_PROMPT),
        TestCase(label="saved_its_own_file", unsaved=False, embedded=False, same_file=True, expected=NO_PROMPT),
        TestCase(label="unsaved_another_file", unsaved=True, embedded=False, same_file=False, expected=SAVE_PROMPT),
        TestCase(label="unsaved_its_own_file", unsaved=True, embedded=False, same_file=True, expected=REPLACED_PROMPT),
        TestCase(label="project_sample_another_file", unsaved=True, embedded=True, same_file=False, expected=NO_PROMPT),
        TestCase(label="project_sample_its_own_file", unsaved=True, embedded=True, same_file=True, expected=NO_PROMPT),
    )

    @staticmethod
    def _coordinator(
        test_case: TestCase,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> ReconstructionCoordinator:
        """A coordinator over the document in ``open.stn``, opened from its file or as a project sample, unsaved or saved as the case says."""
        opened = tmp_path / "open.stn"
        reconstruction_factory().save(opened)
        manager = ReconstructionManager(scheduling=MagicMock())
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=FakeLanguageManager(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=MagicMock(),
        )
        coordinator.set_reconstructions_tab(MagicMock())
        if test_case.embedded:
            manager.load_reconstruction_object(
                Reconstruction.load(opened),
                name=opened.stem,
                voice_id=OPEN_VOICE_ID,
            )
        else:
            manager.load_reconstruction(opened)
        if test_case.unsaved:
            manager.mark_updated()

        return coordinator

    @staticmethod
    def _converted(test_case: TestCase, tmp_path: Path) -> Path:
        """What the conversion wrote: the open file spelled another way, or a file of its own."""
        if not test_case.same_file:
            return tmp_path / "converted.stn"

        (tmp_path / "folder").mkdir()
        return tmp_path / "folder" / ".." / "open.stn"

    @staticmethod
    def _asked(coordinator: ReconstructionCoordinator) -> str:
        dialogs = coordinator._dialogs
        if dialogs.show_save_confirmation.called:
            return SAVE_PROMPT

        if dialogs.show_confirmation.called:
            assert dialogs.show_confirmation.call_args.kwargs["tag"] == TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED
            return REPLACED_PROMPT

        return NO_PROMPT

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_question_put_before_loading(
        self,
        test_case: TestCase,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> None:
        coordinator = self._coordinator(test_case, reconstruction_factory, tmp_path)

        coordinator.load_converted(self._converted(test_case, tmp_path))

        assert self._asked(coordinator) == test_case.expected

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_going_on_loads_what_the_conversion_wrote(
        self,
        test_case: TestCase,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> None:
        coordinator = self._coordinator(test_case, reconstruction_factory, tmp_path)
        converted = self._converted(test_case, tmp_path)

        coordinator.load_converted(converted)
        asked = self._asked(coordinator)
        if asked == SAVE_PROMPT:
            coordinator._dialogs.show_save_confirmation.call_args.kwargs["on_confirm"]()
        elif asked == REPLACED_PROMPT:
            coordinator._dialogs.show_confirmation.call_args.kwargs["on_confirm"]()

        coordinator._tab.load_reconstruction.assert_called_once_with(converted)

    @pytest.mark.parametrize(
        "test_case",
        [test_case for test_case in test_cases if test_case.expected != NO_PROMPT],
        ids=lambda test_case: test_case.label,
    )
    def test_nothing_loads_before_the_answer(
        self,
        test_case: TestCase,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> None:
        coordinator = self._coordinator(test_case, reconstruction_factory, tmp_path)

        coordinator.load_converted(self._converted(test_case, tmp_path))

        coordinator._tab.load_reconstruction.assert_not_called()
        assert coordinator.is_unsaved()

    def test_a_replaced_file_offers_to_discard_the_changes(
        self,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> None:
        """Saving would write the old document over the conversion, so the prompt offers no Save."""
        test_case = next(test_case for test_case in self.test_cases if test_case.expected == REPLACED_PROMPT)
        coordinator = self._coordinator(test_case, reconstruction_factory, tmp_path)

        coordinator.load_converted(self._converted(test_case, tmp_path))

        prompt = coordinator._dialogs.show_confirmation.call_args.kwargs
        assert prompt["message"] == REPLACED_MESSAGE_KEY
        assert prompt["ok_label"] == DISCARD_LABEL_KEY
        coordinator._dialogs.show_save_confirmation.assert_not_called()

    def test_the_save_prompt_saves_the_open_document(
        self,
        reconstruction_factory: ReconstructionFactory,
        tmp_path: Path,
    ) -> None:
        test_case = next(test_case for test_case in self.test_cases if test_case.expected == SAVE_PROMPT)
        coordinator = self._coordinator(test_case, reconstruction_factory, tmp_path)
        coordinator.load_converted(self._converted(test_case, tmp_path))

        outcome = coordinator._dialogs.show_save_confirmation.call_args.kwargs["on_save"]()

        assert outcome is SaveOutcome.WRITTEN
        assert not coordinator.is_unsaved()


class TestTheExitAsksAboutTheReconstruction(BaseTestSuite):
    """Exiting with unsaved changes in a reconstruction of its own asks to save them first. A project
    sample's changes belong to the project, which the exit asks about already."""

    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        unsaved: bool
        embedded: bool

    test_cases = (
        TestCase(label="standalone_unsaved_asks", unsaved=True, embedded=False, expected=True),
        TestCase(label="standalone_saved_goes_on", unsaved=False, embedded=False, expected=False),
        TestCase(label="project_sample_unsaved_goes_on", unsaved=True, embedded=True, expected=False),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_the_exit_asks_only_about_a_standalone_document(self, test_case: TestCase) -> None:
        coordinator = _gating_coordinator(unsaved=test_case.unsaved, embedded=test_case.embedded)
        proceed = MagicMock()

        coordinator.guard_exit(proceed)

        assert coordinator._dialogs.show_save_confirmation.called is test_case.expected
        assert proceed.called is not test_case.expected

    def test_the_answer_lets_the_exit_go_on(self) -> None:
        coordinator = _gating_coordinator(unsaved=True, embedded=False)
        proceed = MagicMock()

        coordinator.guard_exit(proceed)

        prompt = coordinator._dialogs.show_save_confirmation.call_args.kwargs
        assert prompt["on_save"] == coordinator.save
        assert prompt["on_confirm"] is proceed
