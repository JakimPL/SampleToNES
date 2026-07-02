from pathlib import Path

from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterViewModel,
)


def _view_model(*, phase: ConversionPhase, other_operation_active: bool) -> ConverterViewModel:
    return ConverterViewModel(
        phase=phase,
        status_text="",
        progress=0.0,
        progress_overlay="0%",
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
