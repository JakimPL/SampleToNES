from pathlib import Path

import pytest

from sampletones_application.view_model.main.converter import (
    ConversionPhase,
    ConverterAction,
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
        action_label="",
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


class TestPrimaryAction:
    """The one action button cancels while a conversion holds resources and otherwise offers to
    convert; terminal phases present the convert action as they fall back to idle on their own."""

    @pytest.mark.parametrize(
        ("phase", "action"),
        [
            (ConversionPhase.IDLE, ConverterAction.CONVERT),
            (ConversionPhase.WAITING, ConverterAction.CANCEL),
            (ConversionPhase.RUNNING, ConverterAction.CANCEL),
            (ConversionPhase.CANCELLING, ConverterAction.CANCEL),
            (ConversionPhase.COMPLETED, ConverterAction.CONVERT),
            (ConversionPhase.CANCELLED, ConverterAction.CONVERT),
            (ConversionPhase.FAILED, ConverterAction.CONVERT),
        ],
    )
    def test_action_follows_phase(self, phase: ConversionPhase, action: ConverterAction) -> None:
        assert _view_model(phase=phase).primary_action == action


class TestPrimaryActionEnabled:
    """Cancel stays live while running but is withheld once the stop is already in flight; convert
    is live only from an idle panel that has an input selected."""

    @pytest.mark.parametrize(
        ("phase", "enabled"),
        [
            (ConversionPhase.WAITING, True),
            (ConversionPhase.RUNNING, True),
            (ConversionPhase.CANCELLING, False),
        ],
    )
    def test_cancel_enablement(self, phase: ConversionPhase, enabled: bool) -> None:
        assert _view_model(phase=phase).primary_action_enabled is enabled

    @pytest.mark.parametrize(
        "phase",
        [ConversionPhase.COMPLETED, ConversionPhase.CANCELLED, ConversionPhase.FAILED],
    )
    def test_convert_disabled_in_terminal_phases(self, phase: ConversionPhase) -> None:
        assert _view_model(phase=phase).primary_action_enabled is False

    def test_convert_enabled_when_idle_with_input(self) -> None:
        assert _view_model(phase=ConversionPhase.IDLE).primary_action_enabled is True
