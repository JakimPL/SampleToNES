from unittest.mock import MagicMock

import pytest

from sampletones_application.ui.panels.instruction.instruction import GUIInstructionPanel
from sampletones_shared.exceptions import LibraryDisplayError


def _panel(*, plot_error: Exception) -> GUIInstructionPanel:
    """A panel with only the displays ``display_instruction`` touches, bypassing the widget
    construction."""
    panel = GUIInstructionPanel.__new__(GUIInstructionPanel)
    panel.waveform_display = MagicMock()
    panel.waveform_display.load_library_fragment.side_effect = plot_error
    panel.spectrum_display = MagicMock()
    return panel


class TestDisplayInstructionClassification:
    """Rendering classification guard: a data-shape failure that makes the fragment unplottable
    re-raises as ``LibraryDisplayError`` for the coordinator to catch; a failure outside those
    types is a bug and propagates."""

    @pytest.mark.parametrize(
        "error",
        [KeyError("generator"), IndexError("empty histogram"), ValueError("degenerate data")],
        ids=["key", "index", "value"],
    )
    def test_data_shape_failure_raises_library_display_error(self, error: Exception) -> None:
        panel = _panel(plot_error=error)

        with pytest.raises(LibraryDisplayError) as excinfo:
            panel.display_instruction(MagicMock())

        assert excinfo.value.__cause__ is error

    def test_unexpected_failure_propagates(self) -> None:
        panel = _panel(plot_error=RuntimeError("bug"))

        with pytest.raises(RuntimeError):
            panel.display_instruction(MagicMock())
