from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.reconstruction import ReconstructionCoordinator
from sampletones_application.logic.reconstruction.manager import ReconstructionManager
from sampletones_application.services.regeneration import RegeneratedInstrument
from sampletones_application.services.result import ServiceSuccess
from sampletones_core.constants.enums import FeatureKey, GeneratorName
from sampletones_core.reconstructions import Reconstruction
from sampletones_shared.exceptions import (
    InvalidMetadataError,
    InvalidReconstructionValuesError,
)
from tests.conftest import ReconstructionFactory
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


@pytest.fixture
def reconstruction_coordinator() -> ReconstructionCoordinator:
    return ReconstructionCoordinator(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        layout=MagicMock(),
        on_tab_switch=MagicMock(),
        on_session_state_changed=MagicMock(),
        on_reconstruction_updated=MagicMock(),
    )


class TestReconstructionRestoreSuccess:
    def test_loads_and_keeps_session_pointer(self, reconstruction_coordinator: ReconstructionCoordinator) -> None:
        path = Path("lead.stn")

        reconstruction_coordinator.load_reconstruction_safely(path)

        reconstruction_coordinator._reconstruction_manager.load_reconstruction.assert_called_once_with(path)
        reconstruction_coordinator._session_manager.set_current_reconstruction.assert_not_called()


class TestReconstructionRestoreAbsorbsFailures(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        failure: Exception

    test_cases = [
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
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
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
        """Pins the hook-before-apply order in ``_on_updated``.

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
            layout=MagicMock(),
            on_tab_switch=MagicMock(),
            on_session_state_changed=MagicMock(),
            on_reconstruction_updated=lambda _outcome: observed.append(manager.reconstruction),
        )
        coordinator.set_reconstructions_tab(MagicMock())
        regenerated = reconstruction_factory()
        outcome = RegeneratedInstrument(
            reconstruction=regenerated,
            generator_name=GeneratorName.PULSE1,
            feature_key=FeatureKey.VOLUME,
        )

        coordinator._on_regeneration_result(ServiceSuccess(value=outcome))

        assert len(observed) == 1
        assert observed[0] is prior
        assert manager.reconstruction is regenerated


class TestReconstructionRestorePropagatesUnexpected:
    def test_runtime_error_propagates(self, reconstruction_coordinator: ReconstructionCoordinator) -> None:
        reconstruction_coordinator._reconstruction_manager.load_reconstruction.side_effect = RuntimeError("boom")

        with pytest.raises(RuntimeError):
            reconstruction_coordinator.load_reconstruction_safely(Path("lead.stn"))

        reconstruction_coordinator._session_manager.set_current_reconstruction.assert_not_called()
