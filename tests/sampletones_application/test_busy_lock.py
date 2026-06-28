from unittest.mock import MagicMock

from sampletones_application.application import Application


def _application(*, converter_running: bool = False, library_generating: bool = False) -> Application:
    """An application with only the attributes the busy methods touch, bypassing the full composition
    root constructor."""
    application = Application.__new__(Application)
    application._main_tab = MagicMock()
    application._main_tab.is_converter_running.return_value = converter_running
    application._instructions_tab = MagicMock()
    application._instructions_tab.is_library_generating.return_value = library_generating
    application._reconstructions_tab = MagicMock()
    return application


class TestBusySourceOfTruth:
    """``_is_generation_in_progress`` is the single busy authority: a conversion or a library
    generation each make it true, and only an idle pair makes it false."""

    def test_busy_while_converter_runs(self) -> None:
        assert _application(converter_running=True)._is_generation_in_progress() is True

    def test_busy_while_library_generates(self) -> None:
        assert _application(library_generating=True)._is_generation_in_progress() is True

    def test_idle_when_neither_runs(self) -> None:
        assert _application()._is_generation_in_progress() is False


class TestBusyRefreshPropagation:
    """A busy-state change nudges both tabs to re-evaluate their action buttons; each panel reads the
    live busy authority for itself, so no value is pushed."""

    def test_refresh_nudges_both_tabs(self) -> None:
        application = _application()
        application._refresh_busy_state()
        application._reconstructions_tab.refresh_reconstruct_buttons.assert_called_once_with()
        application._instructions_tab.refresh_generate_button.assert_called_once_with()
