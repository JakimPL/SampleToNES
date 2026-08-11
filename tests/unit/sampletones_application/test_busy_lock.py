from unittest.mock import MagicMock

from sampletones_application.application import Application


def _application(
    *,
    converter_running: bool = False,
    library_generating: bool = False,
    rendering: bool = False,
) -> Application:
    """An application with only the attributes the busy methods touch, bypassing the full composition
    root constructor."""
    application = Application.__new__(Application)
    application._main_tab = MagicMock()
    application._main_tab.is_converter_active.return_value = converter_running
    application._instructions_tab = MagicMock()
    application._instructions_tab.is_library_generating.return_value = library_generating
    application._reconstructions_tab = MagicMock()
    application._render_coordinator = MagicMock()
    application._render_coordinator.is_active = rendering
    application._update_menu = MagicMock()
    return application


class TestBusySourceOfTruth:
    """``_is_operation_active`` is the single busy authority: a conversion, a library generation or
    a render each make it true, and only an idle set makes it false."""

    def test_busy_while_converter_runs(self) -> None:
        assert _application(converter_running=True)._is_operation_active() is True

    def test_busy_while_library_generates(self) -> None:
        assert _application(library_generating=True)._is_operation_active() is True

    def test_busy_while_song_renders(self) -> None:
        assert _application(rendering=True)._is_operation_active() is True

    def test_idle_when_none_runs(self) -> None:
        assert _application()._is_operation_active() is False


class TestBusyRefreshPropagation:
    """A busy-state change nudges both tabs to re-evaluate their action buttons and the menu to
    re-read what may start another such operation; each reads the live busy authority for itself,
    so no value is pushed."""

    def test_refresh_nudges_both_tabs(self) -> None:
        application = _application()
        application._refresh_busy_state()
        application._instructions_tab.refresh_generate_button.assert_called_once_with()

    def test_refresh_reaches_the_menu(self) -> None:
        application = _application()
        application._refresh_busy_state()
        application._update_menu.assert_called_once_with()

    def test_a_render_edge_refreshes_the_converter_view(self) -> None:
        application = _application()
        application._on_render_activity_changed()
        application._main_tab.refresh_converter_view.assert_called_once_with()
