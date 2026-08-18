from pathlib import Path
from typing import Dict, Final
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.logic.main.converter import (
    ConversionSuccess,
    ConverterLogic,
)
from sampletones_application.view_model.main.converter import (
    ACTIVE_PHASES,
    ConversionPhase,
    ConverterViewModel,
)
from tests.suite.language import FakeLanguageManager

TEXTS: Final[Dict[str, str]] = {
    "main.converter.label.convert_sample_button": "Convert sample",
    "main.converter.label.convert_directory_button": "Convert directory",
    "main.converter.label.cancel_button": "Cancel",
    "main.converter.template.convert_label_template": "{}: {}",
}


@pytest.fixture
def converter_logic() -> ConverterLogic:
    config_manager = MagicMock()
    config_manager.get_reconstructions_directory.return_value = Path("/tmp/reconstructions")
    service = MagicMock()
    service.is_running.return_value = False
    scheduling = MagicMock(
        priorities=MagicMock(schedule=0),
        delays=MagicMock(schedule=0, cancel=0),
    )
    logic = ConverterLogic(
        config_manager,
        service,
        scheduling=scheduling,
        language_manager=FakeLanguageManager(TEXTS),  # type: ignore[arg-type]
        is_operation_active=lambda: False,
    )
    logic.on_view_changed = MagicMock()
    logic.generate_library = MagicMock()
    logic.is_library_available = lambda: False
    return logic


class TestCancelDuringLibraryGeneration:
    """The converter requests a library when none exists and waits for it. Cancelling during that
    wait must abort the pending conversion and stop the in-flight generation."""

    def test_cancel_while_waiting_cancels_generation_and_finishes(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        cancel_generation = MagicMock()
        on_cancelled = MagicMock()
        converter_logic.cancel_library_generation = cancel_generation
        converter_logic.on_cancelled = on_cancelled

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()
            assert converter_logic._phase == ConversionPhase.WAITING

            converter_logic.cancel()

        cancel_generation.assert_called_once()
        on_cancelled.assert_called_once()
        assert converter_logic._phase == ConversionPhase.CANCELLED

    def test_wait_loop_aborts_once_no_longer_waiting(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
            converter_logic.start_conversion()
            converter_logic.cancel()
            scheduled.reset_mock()

            converter_logic._wait_for_library_and_start()

        converter_logic._service.start.assert_not_called()
        scheduled.assert_not_called()

    def test_wait_poll_does_not_emit_a_zero_progress_view(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        """While waiting, the bar reflects the library-generation progress. A re-poll that finds the
        library still missing must only re-queue itself, never emit its own view: emitting one would
        carry ``progress=0.0`` and momentarily reset the bar."""
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
            converter_logic.start_conversion()
            converter_logic.on_view_changed.reset_mock()
            scheduled.reset_mock()

            converter_logic._wait_for_library_and_start()

        converter_logic.on_view_changed.assert_not_called()
        scheduled.assert_called_once()


class TestNoGeneratorsGuard:
    """With no generators enabled there is nothing to reconstruct, so the conversion must not start."""

    def test_no_generators_notifies_and_does_not_start(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._config_manager.config.generation.generators = []
        on_no_generators = MagicMock()
        converter_logic.on_no_generators = on_no_generators

        converter_logic.start_conversion()

        on_no_generators.assert_called_once()
        converter_logic.generate_library.assert_not_called()
        assert converter_logic._phase == ConversionPhase.IDLE


class TestActivePhases:
    """``is_active`` reports a conversion occupying resources for every non-idle, non-terminal phase —
    covering the WAITING preparation that runs before the service starts."""

    @pytest.mark.parametrize("phase", sorted(ACTIVE_PHASES, key=str))
    def test_active_during_non_terminal_phases(
        self,
        converter_logic: ConverterLogic,
        phase: ConversionPhase,
    ) -> None:
        converter_logic._phase = phase
        assert converter_logic.is_active is True

    @pytest.mark.parametrize(
        "phase",
        [
            ConversionPhase.IDLE,
            ConversionPhase.COMPLETED,
            ConversionPhase.CANCELLED,
            ConversionPhase.FAILED,
        ],
    )
    def test_inactive_when_idle_or_terminal(
        self,
        converter_logic: ConverterLogic,
        phase: ConversionPhase,
    ) -> None:
        converter_logic._phase = phase
        assert converter_logic.is_active is False


def _last_view_model(converter_logic: ConverterLogic) -> ConverterViewModel:
    return converter_logic.on_view_changed.call_args.args[0]


class TestActionLabel:
    """The one action button's label is a projection of converter state, composed where the display
    strings are resolved (the logic layer) rather than glued together in the panel: it names the
    selected input while idle and reads the cancel label once a conversion holds resources.
    """

    def test_idle_file_label_names_the_selected_file(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_file = True
        converter_logic._input_path = Path("/audio/kick.wav")

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert sample: kick.wav"

    def test_idle_directory_label_uses_the_directory_variant(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_file = False
        converter_logic._input_path = Path("/audio/drums")

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert directory: drums"

    def test_idle_without_input_reads_the_bare_convert_label(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._input_path = None

        converter_logic.emit_initial_view()

        assert _last_view_model(converter_logic).action_label == "Convert sample"

    def test_active_conversion_reads_the_cancel_label(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._input_path = Path("/audio/kick.wav")

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        assert _last_view_model(converter_logic).action_label == "Cancel"


class TestStartConversionGate:
    """A conversion refuses to start while another exclusive operation is active, so two heavy
    processes cannot run at once."""

    def test_refuses_when_an_operation_is_active(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic._is_operation_active = lambda: True

        converter_logic.start_conversion()

        converter_logic._service.start.assert_not_called()
        converter_logic.generate_library.assert_not_called()
        assert converter_logic._phase == ConversionPhase.IDLE

    def test_proceeds_when_nothing_is_active(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        with patch("sampletones_application.logic.main.converter.CallbackQueue.add"):
            converter_logic.start_conversion()

        converter_logic.generate_library.assert_called_once()
        assert converter_logic._phase == ConversionPhase.WAITING


class TestAssignPaths:
    """``get_output_path``'s contract is the ``OSError`` family: those failures abort the
    conversion and report through ``on_error``; a failure outside the contract is a bug and
    propagates."""

    @pytest.mark.parametrize(
        "error",
        [FileNotFoundError("missing"), OSError("invalid path")],
        ids=["missing", "invalid"],
    )
    def test_path_failure_reports_error_and_aborts(
        self,
        converter_logic: ConverterLogic,
        error: Exception,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch(
            "sampletones_application.logic.main.converter.get_output_path",
            side_effect=error,
        ):
            result = converter_logic._assign_paths(
                Path("/tmp/input.wav"),
                MagicMock(),
            )

        assert result is False
        converter_logic.on_error.assert_called_once_with(error)

    def test_unexpected_failure_propagates(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with (
            patch(
                "sampletones_application.logic.main.converter.get_output_path",
                side_effect=KeyError("drive"),
            ),
            pytest.raises(KeyError),
        ):
            converter_logic._assign_paths(Path("/tmp/input.wav"), MagicMock())

        converter_logic.on_error.assert_not_called()


class TestConversionCompleteHandsOverOutcome:
    """A completed conversion tells its listener what was produced, so the follow-up load offer can
    target the single reconstruction (file) or the browser (directory)."""

    def test_success_carries_input_kind_and_output_path(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        on_success = MagicMock()
        converter_logic.on_success = on_success
        converter_logic._is_file = True
        converter_logic._output_path = Path("/reconstructions/kick.rcn")

        converter_logic._on_conversion_complete(Path("/reconstructions/kick.rcn"))

        assert converter_logic._phase == ConversionPhase.COMPLETED
        on_success.assert_called_once_with(
            ConversionSuccess(is_file=True, output_path=Path("/reconstructions/kick.rcn"))
        )


class TestFailureReturnsToIdle:
    """With no Close button, a failure reports through ``on_error`` and schedules its own return to
    idle so the panel never strands on the failed phase."""

    def test_failure_schedules_return_to_idle_and_reports(
        self,
        converter_logic: ConverterLogic,
    ) -> None:
        converter_logic.on_error = MagicMock()

        with patch("sampletones_application.logic.main.converter.CallbackQueue.add") as scheduled:
            converter_logic._on_conversion_error(RuntimeError("boom"))

        assert converter_logic._phase == ConversionPhase.FAILED
        scheduled.assert_called_once()
        assert scheduled.call_args.args[0] == converter_logic.close
        converter_logic.on_error.assert_called_once()
