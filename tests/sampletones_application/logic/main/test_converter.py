from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sampletones_application.logic.main.converter import ConverterLogic
from sampletones_application.view_model.main.converter import ConversionPhase


@pytest.fixture
def converter_logic() -> ConverterLogic:
    config_manager = MagicMock()
    config_manager.get_reconstructions_directory.return_value = Path("/tmp/reconstructions")
    service = MagicMock()
    service.is_running.return_value = False
    scheduling = MagicMock(priority_schedule=0, delay_schedule=0, delay_cancel=0)
    language_manager = MagicMock()
    language_manager.__getitem__.return_value = "message"

    logic = ConverterLogic(
        config_manager,
        service,
        scheduling=scheduling,
        language_manager=language_manager,
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
