from pathlib import Path

import pytest

from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)


def _view_model(
    *,
    phase: ConversionPhase,
    other_operation_active: bool = False,
    progress: float = 0.0,
) -> ConverterViewModel:
    return ConverterViewModel(
        phase=phase,
        status_text="",
        progress=progress,
        input_path=Path("/audio/sample.wav"),
        output_path=Path("/reconstructions"),
        is_file=True,
        other_operation_active=other_operation_active,
    )


class TestConvertButtonGating:
    """An input is loaded and the converter is idle, so the only thing that should withhold the Convert
    button is another exclusive operation (a library generating elsewhere)."""

    def test_enabled_when_no_other_operation_active(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, other_operation_active=False)
        assert view_model.convert_button_enabled is True

    def test_disabled_while_another_operation_is_active(self) -> None:
        view_model = _view_model(phase=ConversionPhase.IDLE, other_operation_active=True)
        assert view_model.convert_button_enabled is False


class TestProgressOverlay:
    """The overlay label is a projection of the progress fraction, clamped to the bar's range,
    so a full bar always reads 100% and the label can never disagree with the fill."""

    @pytest.mark.parametrize(
        ("progress", "overlay"),
        [(-0.5, "0%"), (0.0, "0%"), (0.333, "33%"), (0.5, "50%"), (1.0, "100%"), (1.5, "100%")],
    )
    def test_overlay_renders_the_clamped_percentage(self, progress: float, overlay: str) -> None:
        view_model = _view_model(phase=ConversionPhase.RUNNING, progress=progress)
        assert view_model.progress_overlay == overlay
