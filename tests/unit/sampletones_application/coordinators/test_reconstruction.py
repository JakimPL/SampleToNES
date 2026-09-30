from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.coordinators.tabs.reconstruction import (
    ReconstructionTabCoordinator,
)
from sampletones_application.logic.reconstruction.edit import StemRemoval
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.services.regeneration.service import RegeneratedInstrument
from sampletones_application.services.result import ServiceSuccess
from sampletones_application.tags.general import TAG_GLOBAL_DIALOG_RECONSTRUCTION_REPLACED
from sampletones_application.utils.gui.dialogs.outcome import SaveOutcome
from sampletones_core.constants.enums import ChannelName, FeatureKey
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import (
    InvalidMetadataError,
    InvalidReconstructionValuesError,
)
from tests.conftest import ReconstructionFactory
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.language import FakeLanguageManager


@pytest.fixture
def reconstruction_coordinator() -> ReconstructionCoordinator:
    return ReconstructionCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
        is_reconstruction_embedded=MagicMock(return_value=False),
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
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
        is_reconstruction_embedded=lambda: embedded,
    )
    coordinator._reconstruction_manager.session.unsaved_changes = unsaved
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

        The hook locates the owning project sample by identity against the prior
        reconstruction, so it must observe the manager before the document rebinds
        to the regenerated object.
        """
        manager = ReconstructionManager(scheduling=MagicMock())
        prior = reconstruction_factory()
        manager.load_reconstruction_object(prior, name="lead")
        observed: List[Optional[Reconstruction]] = []
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=lambda _outcome: observed.append(manager.reconstruction),
            is_reconstruction_embedded=lambda: False,
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
        manager.load_reconstruction_object(prior, name="lead")
        observed: List[Optional[Reconstruction]] = []
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=lambda _edit: observed.append(manager.reconstruction),
            is_reconstruction_embedded=lambda: False,
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

        tab.redraw_reconstruction.assert_called_once_with()
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
        """A coordinator over a document loaded from ``open.stn``, unsaved or saved as the case says."""
        opened = tmp_path / "open.stn"
        reconstruction_factory().save(opened)
        manager = ReconstructionManager(scheduling=MagicMock())
        coordinator = ReconstructionCoordinator(
            manager,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            dialogs=MagicMock(),
            language_manager=FakeLanguageManager(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=MagicMock(),
            is_reconstruction_embedded=lambda: test_case.embedded,
        )
        coordinator.set_reconstructions_tab(MagicMock())
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
