from typing import Any, Dict, Final
from unittest.mock import MagicMock

import pytest

from sampletones_application.coordinators.tabs.sequencer.nes_frequency import NesFrequencyChange
from sampletones_application.logic.history.action import HistoryAction
from tests.suite.language import FakeLanguageManager

PROJECT_RATE: Final[int] = 60
NEW_RATE: Final[int] = 30


@pytest.fixture
def tracker_logic() -> MagicMock:
    logic = MagicMock()
    logic.settings.nes_frequency = PROJECT_RATE
    return logic


@pytest.fixture
def project_controller() -> MagicMock:
    controller = MagicMock()
    controller.has_voices = True
    return controller


@pytest.fixture
def history() -> MagicMock:
    return MagicMock()


@pytest.fixture
def dialogs() -> MagicMock:
    return MagicMock()


@pytest.fixture
def on_changed() -> MagicMock:
    return MagicMock()


@pytest.fixture
def change(
    tracker_logic: MagicMock,
    project_controller: MagicMock,
    history: MagicMock,
    dialogs: MagicMock,
    on_changed: MagicMock,
) -> NesFrequencyChange:
    """A change over a project at ``PROJECT_RATE`` that holds samples."""
    return NesFrequencyChange(
        tracker_logic,
        project_controller,
        history,
        MagicMock(),
        dialogs=dialogs,
        language_manager=FakeLanguageManager(),
        on_changed=on_changed,
    )


def _answers(dialogs: MagicMock) -> Dict[str, Any]:
    """The handlers the question hands the dialog, by the answer each one stands for."""
    answers: Dict[str, Any] = dialogs.show_confirmation.call_args.kwargs
    return answers


class TestRequestNesFrequencyChange:
    @pytest.mark.parametrize("acknowledged", [False, True])
    def test_the_project_rate_changes_nothing(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        dialogs: MagicMock,
        on_changed: MagicMock,
        acknowledged: bool,
    ) -> None:
        change.acknowledged = acknowledged

        change.request(PROJECT_RATE)

        tracker_logic.set_nes_frequency.assert_not_called()
        dialogs.show_confirmation.assert_not_called()
        on_changed.assert_not_called()

    def test_applies_without_confirmation_when_no_samples(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        project_controller: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        project_controller.has_voices = False

        change.request(NEW_RATE)

        tracker_logic.set_nes_frequency.assert_called_once_with(NEW_RATE)
        dialogs.show_confirmation.assert_not_called()

    def test_applies_without_confirmation_once_acknowledged(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        change.acknowledged = True

        change.request(NEW_RATE)

        tracker_logic.set_nes_frequency.assert_called_once_with(NEW_RATE)
        dialogs.show_confirmation.assert_not_called()

    def test_prompts_before_applying_when_samples_exist(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        dialogs: MagicMock,
    ) -> None:
        change.request(NEW_RATE)
        tracker_logic.set_nes_frequency.assert_not_called()

        _answers(dialogs)["on_confirm"]()

        tracker_logic.set_nes_frequency.assert_called_once_with(NEW_RATE)

    def test_applying_records_one_entry_keyed_by_the_rate(
        self,
        change: NesFrequencyChange,
        history: MagicMock,
    ) -> None:
        """The retune results fold back into the entry the rate keys, so one undo restores both."""
        change.acknowledged = True

        change.request(NEW_RATE)

        history.transaction.assert_called_once()
        assert history.transaction.call_args.args == (HistoryAction.SET_NES_FREQUENCY,)
        assert history.transaction.call_args.kwargs["coalesce"] == (NEW_RATE,)

    def test_applying_requests_a_retune_of_the_samples(
        self,
        change: NesFrequencyChange,
        dialogs: MagicMock,
        on_changed: MagicMock,
    ) -> None:
        change.request(NEW_RATE)

        _answers(dialogs)["on_confirm"]()

        on_changed.assert_called_once_with(NEW_RATE)

    def test_a_refused_rate_requests_no_retune(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        on_changed: MagicMock,
    ) -> None:
        """A rate the project refuses leaves the samples as they are, so nothing asks to re-time them."""
        change.acknowledged = True
        tracker_logic.set_nes_frequency.side_effect = ValueError("refused")

        with pytest.raises(ValueError):
            change.request(NEW_RATE)

        on_changed.assert_not_called()

    def test_opt_out_acknowledges_for_the_session(self, change: NesFrequencyChange, dialogs: MagicMock) -> None:
        change.request(NEW_RATE)

        _answers(dialogs)["on_opt_out"]()

        assert change.acknowledged is True

    def test_cancel_restores_the_field_and_applies_nothing(
        self,
        change: NesFrequencyChange,
        tracker_logic: MagicMock,
        dialogs: MagicMock,
        on_changed: MagicMock,
    ) -> None:
        change.request(NEW_RATE)

        _answers(dialogs)["on_cancel"]()

        tracker_logic.push_settings.assert_called_once()
        tracker_logic.set_nes_frequency.assert_not_called()
        on_changed.assert_not_called()
