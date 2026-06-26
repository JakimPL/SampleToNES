from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.coordinators.sequencer import SequencerTabCoordinator


@pytest.fixture
def coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators ``import_reconstruction`` touches.

    The full constructor builds the sequencer's GUI subtree (themes, fonts, synthesiser), which
    is out of scope here; only the import orchestration is under test.
    """
    instance = object.__new__(SequencerTabCoordinator)
    instance._project_controller = MagicMock()
    instance._sequencer_browser_logic = MagicMock()
    instance._dialogs = MagicMock()
    instance._on_tab_switch = MagicMock()
    instance._msg_no_project = "no project"
    instance._ttl_no_project = "No project open"
    return instance


@pytest.fixture
def samples_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the samples-menu handlers touch."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._sequencer_samples_logic = MagicMock()
    instance._dialogs = MagicMock()
    instance._ttl_remove_sample = "Remove sample"
    instance._msg_remove_sample = "Remove {name}?"
    instance._lbl_remove_sample = "Remove"
    return instance


class TestRemoveSample:
    def test_unused_sample_is_removed_without_confirmation(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._sequencer_samples_logic.is_sample_used.return_value = False

        samples_coordinator._remove_sample("abc")

        samples_coordinator._sequencer_samples_logic.remove_sample.assert_called_once_with("abc")
        samples_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_used_sample_prompts_confirmation_before_removing(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        logic = samples_coordinator._sequencer_samples_logic
        logic.is_sample_used.return_value = True
        logic.sample_name.return_value = "lead"

        samples_coordinator._remove_sample("abc")

        samples_coordinator._dialogs.show_confirmation.assert_called_once()
        logic.remove_sample.assert_not_called()

        confirmation = samples_coordinator._dialogs.show_confirmation.call_args.kwargs
        assert confirmation["message"] == "Remove lead?"

        confirmation["on_confirm"]()
        logic.remove_sample.assert_called_once_with("abc")


class TestSubmitRename:
    def test_submit_rename_trims_whitespace(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._submit_rename("abc", "  bass  ")

        samples_coordinator._sequencer_samples_logic.rename_sample.assert_called_once_with("abc", "bass")

    def test_submit_rename_ignores_blank_name(
        self,
        samples_coordinator: SequencerTabCoordinator,
    ) -> None:
        samples_coordinator._submit_rename("abc", "   ")

        samples_coordinator._sequencer_samples_logic.rename_sample.assert_not_called()


@pytest.fixture
def nes_frequency_coordinator() -> SequencerTabCoordinator:
    """A coordinator with only the collaborators the NES-frequency change handler touches."""
    instance = object.__new__(SequencerTabCoordinator)
    instance._sequencer_grid_logic = MagicMock()
    instance._sequencer_grid_logic.settings.nes_frequency = 60
    instance._project_controller = MagicMock()
    instance._project_controller.has_samples = True
    instance._dialogs = MagicMock()
    instance._nes_frequency_change_acknowledged = False
    instance._ttl_change_nes_frequency = "Change NES frequency"
    instance._msg_change_nes_frequency = "Re-times samples. Continue?"
    instance._lbl_change_nes_frequency = "Change"
    instance._lbl_dont_ask_again = "Don't ask again"
    return instance


class TestRequestNesFrequencyChange:
    def test_unchanged_value_does_nothing(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(60)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_when_no_samples(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._project_controller.has_samples = False

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_once_acknowledged(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._nes_frequency_change_acknowledged = True

        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)
        nes_frequency_coordinator._dialogs.show_confirmation.assert_not_called()

    def test_prompts_before_applying_when_samples_exist(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        nes_frequency_coordinator._dialogs.show_confirmation.assert_called_once()
        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_not_called()

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_confirm"]()
        nes_frequency_coordinator._sequencer_grid_logic.set_nes_frequency.assert_called_once_with(30)

    def test_opt_out_acknowledges_for_the_session(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_opt_out"]()

        assert nes_frequency_coordinator._nes_frequency_change_acknowledged is True

    def test_cancel_restores_the_field(
        self,
        nes_frequency_coordinator: SequencerTabCoordinator,
    ) -> None:
        nes_frequency_coordinator._request_nes_frequency_change(30)

        confirmation = nes_frequency_coordinator._dialogs.show_confirmation.call_args.kwargs
        confirmation["on_cancel"]()

        nes_frequency_coordinator._sequencer_grid_logic.push_settings.assert_called_once()


class TestImportReconstruction:
    def test_closed_project_shows_dialog_and_does_not_import(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.is_open = False

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_info.assert_called_once()
        coordinator._sequencer_browser_logic.import_reconstruction.assert_not_called()
        coordinator._on_tab_switch.assert_not_called()

    def test_successful_import_switches_to_sequencer_tab(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.is_open = True
        filepath = Path("reconstruction.stn")

        coordinator.import_reconstruction(filepath)

        coordinator._sequencer_browser_logic.import_reconstruction.assert_called_once_with(filepath)
        coordinator._on_tab_switch.assert_called_once_with(Tab.SEQUENCER)
        coordinator._dialogs.show_info.assert_not_called()

    def test_failed_import_does_not_switch_tab(
        self,
        coordinator: SequencerTabCoordinator,
    ) -> None:
        coordinator._project_controller.is_open = True
        coordinator._sequencer_browser_logic.import_reconstruction.side_effect = ValueError("invalid")

        coordinator.import_reconstruction(Path("reconstruction.stn"))

        coordinator._dialogs.show_error.assert_called_once()
        coordinator._on_tab_switch.assert_not_called()
