from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.elements.global_ import GlobalMessageElements
from sampletones_application.config.managers.outcome import (
    ConfigLoadFailure,
    ConfigLoadFailureReason,
    ConfigRecovered,
)
from sampletones_application.coordinators.config import ConfigCoordinator


def _coordinator(config_manager: MagicMock) -> ConfigCoordinator:
    return ConfigCoordinator(
        config_manager,
        MagicMock(),
        dialogs=MagicMock(),
        language_manager=MagicMock(),
        layout=MagicMock(),
    )


def _manager_with(*outcomes: object, config_path: Path = Path("config.json")) -> MagicMock:
    config_manager = MagicMock()
    config_manager.config_path = config_path
    config_manager.pending_load_outcomes = list(outcomes)
    return config_manager


@dataclass(frozen=True)
class ReasonCase:
    label: str
    reason: ConfigLoadFailureReason
    element: GlobalMessageElements


reason_cases = [
    ReasonCase("load", ConfigLoadFailureReason.LOAD_ERROR, GlobalMessageElements.CONFIGURATION_LOAD_ERROR),
    ReasonCase("parse", ConfigLoadFailureReason.PARSE_ERROR, GlobalMessageElements.CONFIGURATION_PARSE_ERROR),
    ReasonCase("invalid", ConfigLoadFailureReason.INVALID, GlobalMessageElements.CONFIGURATION_INVALID_ERROR),
]


class TestPresentPendingLoadOutcomes:
    def test_recovered_outcome_shows_recovery_dialog(self, tmp_path: Path) -> None:
        config_path = tmp_path / "config.json"
        config_manager = _manager_with(
            ConfigRecovered(source_version="1.0.0", dropped=(("generation", "drive"), ("obsolete_field",))),
            config_path=config_path,
        )
        coordinator = _coordinator(config_manager)

        coordinator.present_pending_load_outcomes()

        coordinator._dialogs.show_config_recovery.assert_called_once()
        kwargs = coordinator._dialogs.show_config_recovery.call_args.kwargs
        assert kwargs["config_path"] == config_path
        assert kwargs["source_version"] == "1.0.0"
        assert set(kwargs["properties"]) == {"generation.drive", "obsolete_field"}
        coordinator._dialogs.show_error.assert_not_called()

    @pytest.mark.parametrize("case", reason_cases, ids=lambda case: case.label)
    def test_failure_outcome_shows_error_with_mapped_message(self, case: ReasonCase) -> None:
        config_manager = _manager_with(ConfigLoadFailure(RuntimeError("boom"), case.reason))
        coordinator = _coordinator(config_manager)

        coordinator.present_pending_load_outcomes()

        coordinator._dialogs.show_error.assert_called_once()
        lookup_key = coordinator._language_manager.__getitem__.call_args.args[0]
        assert lookup_key[3] is case.element
        coordinator._dialogs.show_config_recovery.assert_not_called()

    def test_outcomes_are_cleared_after_presenting(self) -> None:
        config_manager = _manager_with(ConfigLoadFailure(RuntimeError("boom"), ConfigLoadFailureReason.LOAD_ERROR))
        coordinator = _coordinator(config_manager)

        coordinator.present_pending_load_outcomes()

        assert config_manager.pending_load_outcomes == []

    def test_no_outcomes_presents_nothing(self) -> None:
        coordinator = _coordinator(_manager_with())

        coordinator.present_pending_load_outcomes()

        coordinator._dialogs.show_config_recovery.assert_not_called()
        coordinator._dialogs.show_error.assert_not_called()
