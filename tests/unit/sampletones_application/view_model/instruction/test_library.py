import pytest

from sampletones_application.view_model.instruction.library import LibraryPanelViewModel


def _view_model(*, generating: bool, progress: float = 0.0) -> LibraryPanelViewModel:
    return LibraryPanelViewModel(
        status_text="",
        generate_button_label="Generate",
        is_generating=generating,
        progress_value=progress,
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


class TestProgressOverlay:
    """The overlay label is a projection of the progress fraction, clamped to the bar's range,
    so a full bar always reads 100% and the label can never disagree with the fill."""

    @pytest.mark.parametrize(
        ("progress", "overlay"),
        [
            (-0.5, "0%"),
            (0.0, "0%"),
            (0.333, "33%"),
            (0.5, "50%"),
            (1.0, "100%"),
            (1.5, "100%"),
        ],
    )
    def test_overlay_renders_the_clamped_percentage(self, progress: float, overlay: str) -> None:
        view_model = _view_model(generating=True, progress=progress)
        assert view_model.progress_overlay == overlay
