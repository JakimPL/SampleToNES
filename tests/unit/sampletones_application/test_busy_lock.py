from pathlib import Path
from unittest.mock import MagicMock

from sampletones_application.application import Application
from sampletones_application.services.export.kind import ExportKind
from sampletones_application.services.export.success import ExportSuccess
from sampletones_application.services.result import ServiceProgress, ServiceStarted
from sampletones_core.exports.stage import ExportStage

NOTHING_MEASURED: int = 0
BYTES_SO_FAR: int = 812


def _application(
    *,
    converter_running: bool = False,
    library_generating: bool = False,
    rendering: bool = False,
    exporting: bool = False,
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
    application.export_service = MagicMock()
    application.export_service.is_running.return_value = exporting
    application._update_menu = MagicMock()
    return application


class TestBusySourceOfTruth:
    """``_is_operation_active`` is the single busy authority: a conversion, a library generation, a
    render or an export each make it true, and only an idle set makes it false."""

    def test_busy_while_converter_runs(self) -> None:
        assert _application(converter_running=True)._is_operation_active() is True

    def test_busy_while_library_generates(self) -> None:
        assert _application(library_generating=True)._is_operation_active() is True

    def test_busy_while_song_renders(self) -> None:
        assert _application(rendering=True)._is_operation_active() is True

    def test_busy_while_an_export_writes(self) -> None:
        assert _application(exporting=True)._is_operation_active() is True

    def test_idle_when_none_runs(self) -> None:
        assert _application()._is_operation_active() is False


class TestExportEdges:
    """An export claims the application while it writes, so its start and its end are busy edges."""

    def test_a_start_refreshes_the_busy_state(self) -> None:
        application = _application()
        application._on_export_activity(ServiceStarted(total=NOTHING_MEASURED))
        application._update_menu.assert_called_once_with()

    def test_a_report_mid_run_is_no_edge(self) -> None:
        application = _application()
        application._on_export_activity(
            ServiceProgress(
                completed=BYTES_SO_FAR,
                total=NOTHING_MEASURED,
                current_item=ExportStage.COMPRESSING,
            )
        )
        application._update_menu.assert_not_called()

    def test_a_finished_export_refreshes_the_busy_state(self) -> None:
        application = _application()
        application._on_export_activity(
            ExportSuccess(
                kind=ExportKind.SAMPLE,
                filepath=Path("song.nsf"),
                export_format=None,
                truncation=None,
            )
        )
        application._update_menu.assert_called_once_with()


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
