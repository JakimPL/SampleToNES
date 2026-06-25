from sampletones_application.view_model.instruction.library import LibraryPanelViewModel


def _view_model(*, generating: bool) -> LibraryPanelViewModel:
    return LibraryPanelViewModel(
        status_text="",
        generate_button_label="Generate",
        is_generating=generating,
        progress_value=0.0,
        progress_overlay="",
    )


class TestLibraryPanelButtonVisibility:
    """While a generation runs the Cancel button replaces Refresh; when idle the reverse holds."""

    def test_idle_shows_refresh_and_generate_hides_cancel(self) -> None:
        view_model = _view_model(generating=False)
        assert view_model.refresh_button_visible is True
        assert view_model.generate_button_visible is True
        assert view_model.cancel_button_visible is False
        assert view_model.progress_visible is False

    def test_generating_shows_cancel_and_progress_hides_idle_controls(self) -> None:
        view_model = _view_model(generating=True)
        assert view_model.refresh_button_visible is False
        assert view_model.generate_button_visible is False
        assert view_model.cancel_button_visible is True
        assert view_model.progress_visible is True
