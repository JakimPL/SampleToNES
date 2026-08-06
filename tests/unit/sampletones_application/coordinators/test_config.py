from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from sampletones_application.categories.key.text import compose_text_key
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
    )


def _manager_with(*outcomes: Any, config_path: Path = Path("config.json")) -> MagicMock:
    config_manager = MagicMock()
    config_manager.config_path = config_path
    config_manager.pending_load_outcomes = list(outcomes)
    return config_manager


@dataclass(frozen=True)
class ReasonCase:
    label: str
    reason: ConfigLoadFailureReason
    key: str


reason_cases = [
    ReasonCase("load", ConfigLoadFailureReason.LOAD_ERROR, "global.dialog.message.configuration_load_error"),
    ReasonCase("parse", ConfigLoadFailureReason.PARSE_ERROR, "global.dialog.message.configuration_parse_error"),
    ReasonCase("invalid", ConfigLoadFailureReason.INVALID, "global.dialog.message.configuration_invalid_error"),
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
        assert compose_text_key(lookup_key) == case.key
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


class TestHandleSave:
    """A save failure within the save contract (``OSError`` family, ``ValueError`` for an empty
    configuration) surfaces the save-failed error dialog; a failure outside the contract is a
    bug and propagates."""

    @pytest.mark.parametrize(
        "error",
        [PermissionError("denied"), ValueError("No configuration to save")],
        ids=["io", "empty"],
    )
    def test_save_failure_shows_the_error_dialog(self, error: Exception, tmp_path: Path) -> None:
        config_manager = _manager_with()
        config_manager.save_config_to_file.side_effect = error
        coordinator = _coordinator(config_manager)

        coordinator._handle_save(tmp_path / "config.json")

        coordinator._dialogs.show_error.assert_called_once()
        assert coordinator._dialogs.show_error.call_args.args[0] is error

    def test_unexpected_save_failure_propagates(self, tmp_path: Path) -> None:
        config_manager = _manager_with()
        config_manager.save_config_to_file.side_effect = RuntimeError("bug")
        coordinator = _coordinator(config_manager)

        with pytest.raises(RuntimeError):
            coordinator._handle_save(tmp_path / "config.json")

        coordinator._dialogs.show_error.assert_not_called()
