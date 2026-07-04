from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.reconstructions import ReconstructionsTabCoordinator
from sampletones_shared.exceptions import UnhandledReconstructionError


@pytest.fixture
def coordinator() -> ReconstructionsTabCoordinator:
    """A coordinator with only the collaborators ``load_reconstruction`` touches, bypassing the
    heavy constructor."""
    instance = object.__new__(ReconstructionsTabCoordinator)
    instance._browser_panel = MagicMock()
    instance._reconstruction_manager = MagicMock()
    instance._dialogs = MagicMock()
    instance._msg_load_error = "load error"
    return instance


class TestLoadReconstructionTail:
    """The load pipeline wraps every unclassified deserialize failure in a
    ``LoadReconstructionError`` subtype, so the ladder's tail presents those with the generic
    load-error dialog; a failure outside the load contract is a bug and propagates. The browser
    unlocks either way."""

    def test_unclassified_load_error_shows_the_generic_dialog(
        self,
        coordinator: ReconstructionsTabCoordinator,
    ) -> None:
        error = UnhandledReconstructionError("wrapped")
        coordinator._reconstruction_manager.load_reconstruction.side_effect = error

        coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_called_once_with(error, "load error")
        coordinator._browser_panel.unlock.assert_called_once_with()

    def test_unexpected_error_propagates_and_unlocks(
        self,
        coordinator: ReconstructionsTabCoordinator,
    ) -> None:
        coordinator._reconstruction_manager.load_reconstruction.side_effect = RuntimeError("bug")

        with pytest.raises(RuntimeError):
            coordinator.load_reconstruction(Path("sample.stn"))

        coordinator._dialogs.show_error.assert_not_called()
        coordinator._browser_panel.unlock.assert_called_once_with()
