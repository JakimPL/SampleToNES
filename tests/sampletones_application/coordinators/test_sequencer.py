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
