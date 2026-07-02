from sampletones_application.view_model.instruction.library import LibraryPanelViewModel


def _view_model(*, generating: bool) -> LibraryPanelViewModel:
    return LibraryPanelViewModel(
        status_text="",
        generate_button_label="Generate",
        is_generating=generating,
        progress_value=0.0,
        progress_overlay="",
    )


class TestLibraryPanelControlsVisibility:
    """The idle controls (refresh + generate) and the generating controls (progress + cancel) are
    mutually exclusive, toggled as whole groups by the generation state."""

    def test_idle_shows_idle_controls_hides_generating(self) -> None:
        view_model = _view_model(generating=False)
        assert view_model.idle_controls_visible is True
        assert view_model.generating_controls_visible is False

    def test_generating_shows_generating_controls_hides_idle(self) -> None:
        view_model = _view_model(generating=True)
        assert view_model.idle_controls_visible is False
        assert view_model.generating_controls_visible is True
