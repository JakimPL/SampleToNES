from typing import Dict, Final, Tuple
from unittest.mock import patch

import pytest

from sampletones_application.ui.elements.graphs import graph as graph_module
from sampletones_application.ui.elements.graphs.graph import GUIGraph
from sampletones_application.ui.elements.graphs.spectrum import GUISpectrumGraph
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.utils.gui.keyboard.modifiers import ALT, NO_MODIFIERS, SHIFT, ModifierSet

MODULE: Final[str] = "sampletones_application.ui.elements.graphs.graph"
X_AXIS: Final[str] = "graph.x"
Y_AXIS: Final[str] = "graph.y"


def _graph() -> GUIWaveformGraph:
    graph = GUIWaveformGraph.__new__(GUIWaveformGraph)
    graph.x_axis_tag = X_AXIS
    graph.y_axis_tag = Y_AXIS
    return graph


class TestReleasingTheAxes:
    """The release follows the frame that states the locks, and waits on no frame to do it."""

    def test_the_release_waits_on_no_frame(self) -> None:
        graph = _graph()

        with (
            patch(f"{MODULE}.FrameCallbackManager"),
            patch.object(graph_module.dpg, "split_frame") as split_frame,
        ):
            graph._release_axes_limits()

        split_frame.assert_not_called()

    def test_the_release_is_scheduled_for_the_following_frame(self) -> None:
        graph = _graph()

        with (
            patch(f"{MODULE}.FrameCallbackManager") as frame,
            patch.object(graph_module.dpg, "set_axis_limits_auto") as set_auto,
        ):
            graph._release_axes_limits()
            set_auto.assert_not_called()
            frame.set_frame_callback.assert_called_once_with(graph._set_axes_auto)
            frame.set_frame_callback.call_args.args[0]()

        assert [call.args[0] for call in set_auto.call_args_list] == [X_AXIS, Y_AXIS]


class TestWhichAxesTheHoverLocks:
    """The wheel zooms the axis left free, so what the hover locks decides what a wheel does."""

    @staticmethod
    def _locks(modifiers: ModifierSet) -> Dict[str, Tuple[bool, bool]]:
        graph = _graph()
        locks: Dict[str, Tuple[bool, bool]] = {}
        with (
            patch(f"{MODULE}.FrameCallbackManager"),
            patch(f"{MODULE}.capture_modifiers", return_value=modifiers),
            patch.object(
                graph_module.dpg,
                "configure_item",
                side_effect=lambda axis, lock_min, lock_max: locks.update({axis: (lock_min, lock_max)}),
            ),
        ):
            GUIGraph._on_hover(graph, 0, 0, None)

        return locks

    @pytest.mark.parametrize(
        ("modifiers", "x_locked", "y_locked"),
        [
            (NO_MODIFIERS, False, True),
            (SHIFT, True, False),
            (ALT, True, True),
            (ALT | SHIFT, True, True),
        ],
        ids=["bare wheel zooms x", "shift zooms y", "alt pans x", "alt and shift pan y"],
    )
    def test_the_hover_locks_every_axis_the_wheel_leaves_alone(
        self,
        modifiers: ModifierSet,
        x_locked: bool,
        y_locked: bool,
    ) -> None:
        locks = self._locks(modifiers)

        assert locks[X_AXIS] == (x_locked, x_locked)
        assert locks[Y_AXIS] == (y_locked, y_locked)


class TestWhichGraphsPan:
    def test_the_waveform_pans_with_the_wheel(self) -> None:
        assert GUIWaveformGraph.pans_with_wheel

    def test_the_spectrum_keeps_its_view(self) -> None:
        assert not GUISpectrumGraph.pans_with_wheel
