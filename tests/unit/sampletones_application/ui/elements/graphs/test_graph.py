from typing import Final
from unittest.mock import patch

from sampletones_application.ui.elements.graphs import graph as graph_module
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph

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
