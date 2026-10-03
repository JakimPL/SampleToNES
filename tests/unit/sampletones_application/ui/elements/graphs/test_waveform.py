from types import SimpleNamespace
from typing import Any, Dict, List, Tuple, Union
from unittest.mock import MagicMock

import numpy as np
import pytest

from sampletones_application.ui.elements.graphs import waveform as waveform_module
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.utils.palette.colors.written import LiteralColor
from sampletones_application.view_model.shared.waveform_data import WaveformData

VOICE_SAMPLES = 64


class _FakeDPG:
    def __init__(self) -> None:
        self.alias_to_id: Dict[str, int] = {}
        self.id_to_alias: Dict[int, str] = {}
        self.children: Dict[str, List[int]] = {}
        self.deleted: List[int] = []
        self.configured: List[str] = []
        self._counter = 1

    def register(self, alias: str) -> int:
        if alias not in self.alias_to_id:
            item_id = self._counter
            self._counter += 1
            self.alias_to_id[alias] = item_id
            self.id_to_alias[item_id] = alias

        return self.alias_to_id[alias]

    def set_children(self, tag: str, aliases: List[str]) -> None:
        self.children[tag] = [self.register(alias) for alias in aliases]

    def does_item_exist(self, tag: str) -> bool:
        if tag == "axis":
            return True

        return any(tag == self.id_to_alias.get(child) for children in self.children.values() for child in children)

    def get_item_children(self, tag: str, slot: int) -> List[int]:
        assert slot == 1
        return list(self.children.get(tag, []))

    def get_item_alias(self, item_id: int) -> str:
        return self.id_to_alias.get(item_id, "")

    def delete_item(self, item: Union[int, str]) -> None:
        item_id = self.alias_to_id.get(item, -1) if isinstance(item, str) else item
        self.deleted.append(item_id)
        for children in self.children.values():
            if item_id in children:
                children.remove(item_id)


@pytest.fixture
def fake_dpg(monkeypatch: pytest.MonkeyPatch) -> _FakeDPG:
    instance = _FakeDPG()
    monkeypatch.setattr(waveform_module.dpg, "does_item_exist", instance.does_item_exist)
    monkeypatch.setattr(waveform_module.dpg, "get_item_children", instance.get_item_children)
    monkeypatch.setattr(waveform_module.dpg, "get_item_alias", instance.get_item_alias)
    monkeypatch.setattr(waveform_module, "dpg_delete_item", instance.delete_item)
    monkeypatch.setattr(
        waveform_module.dpg,
        "configure_item",
        lambda *args, **kwargs: instance.configured.append(args[0]),
    )
    monkeypatch.setattr(waveform_module.dpg, "add_line_series", lambda *args, **kwargs: None)
    monkeypatch.setattr(waveform_module, "dpg_bind_item_theme", lambda *args, **kwargs: None)
    monkeypatch.setattr(waveform_module.dpg, "theme", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(waveform_module.dpg, "theme_component", lambda *args, **kwargs: _DummyContext())
    monkeypatch.setattr(waveform_module.dpg, "add_theme_color", lambda *args, **kwargs: None)
    return instance


class _DummyContext:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None


class _Layer:
    def __init__(self, name: str) -> None:
        self.name = name
        self.x_data = _Array()
        self.y_data = _Array()
        self.color = LiteralColor((255, 255, 255, 255))


class _Array:
    size = 1

    def tolist(self) -> List[float]:
        return [0.0]


def _graph() -> GUIWaveformGraph:
    graph = GUIWaveformGraph.__new__(GUIWaveformGraph)
    graph.y_axis_tag = "axis"
    graph.x_axis_tag = "time_axis"
    graph._named_span = None
    graph._sample_rate = 0
    graph.position_indicator_tag = "indicator"
    graph.overlay_rectangle_tag = "overlay"
    graph.layers = {}
    graph._reconstruction_dimmed = False
    graph._lbl_waveform_reconstruction = "Reconstruction"
    graph._status_bar = MagicMock()
    graph._msg_regenerating = "Regenerating reconstruction..."
    graph.tag = "waveform"
    graph._series_themes = {}
    return graph


def _with_layout(graph: GUIWaveformGraph, opacity: float = 0.4) -> None:
    graph._layout = SimpleNamespace(  # type: ignore[assignment]
        colors=SimpleNamespace(waveform_reconstruction=LiteralColor((255, 200, 100, 255))),
        waveform=SimpleNamespace(reconstruction_dim_opacity=opacity),
    )


class TestWaveformUpdateDisplay:
    def test_removes_stale_series_when_layers_are_cleared(self, fake_dpg: _FakeDPG) -> None:
        graph = _graph()
        fake_dpg.set_children("axis", ["stale", "indicator", "overlay"])

        graph._update_display()

        assert fake_dpg.deleted == [fake_dpg.alias_to_id["stale"]]

    def test_keeps_current_series_and_helper_items(self, fake_dpg: _FakeDPG) -> None:
        graph = _graph()
        graph.layers = {"Sample Name": _Layer("Sample Name")}
        current_series = graph._series_tag("Sample Name")
        fake_dpg.set_children("axis", [current_series, "indicator", "overlay"])

        graph._update_display()

        assert fake_dpg.deleted == []

    def test_preserves_position_indicator_across_updates(self, fake_dpg: _FakeDPG) -> None:
        graph = _graph()
        fake_dpg.set_children("axis", ["indicator", "overlay"])

        graph._update_display()

        assert fake_dpg.alias_to_id["indicator"] not in fake_dpg.deleted
        assert fake_dpg.alias_to_id["overlay"] not in fake_dpg.deleted


class TestWaveformDataUpdateRefit:
    """A retune moves the audio's own length, so its update re-fits the view; an ordinary edit,
    which changes nothing about the length, leaves the reader's view where it was."""

    @staticmethod
    def _waveform_data() -> WaveformData:
        approximation = np.zeros(VOICE_SAMPLES, dtype=np.float32)
        return WaveformData(
            original_audio=None,
            approximation=approximation,
            approximations={},
            coefficient=1.0,
            frame_length=1,
            sample_rate=44100,
        )

    def test_a_refit_update_recomputes_the_axis_ranges(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = _graph()
        graph.current_data = self._waveform_data()
        monkeypatch.setattr(graph, "_display_layers", lambda *_args, **_kwargs: [_Layer("Reconstruction")])
        ranges = MagicMock()
        monkeypatch.setattr(graph, "_update_ranges", ranges)

        graph.update_waveform_data(self._waveform_data(), refit=True)

        ranges.assert_called_once_with()

    def test_an_ordinary_update_leaves_the_ranges_alone(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = _graph()
        graph.current_data = self._waveform_data()
        monkeypatch.setattr(graph, "_display_layers", lambda *_args, **_kwargs: [_Layer("Reconstruction")])
        ranges = MagicMock()
        monkeypatch.setattr(graph, "_update_ranges", ranges)

        graph.update_waveform_data(self._waveform_data())

        ranges.assert_not_called()

    def test_a_graph_not_yet_holding_waveform_data_takes_no_update(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A voice's own waveform (`current_data` unset) has no length to lose, so a retune
        elsewhere reaching this graph by mistake is a no-op rather than a crash."""
        graph = _graph()
        graph.current_data = None
        ranges = MagicMock()
        monkeypatch.setattr(graph, "_update_ranges", ranges)

        graph.update_waveform_data(self._waveform_data(), refit=True)

        ranges.assert_not_called()


class TestAnUpdateDrawsTheLayersItsDataDisplays:
    """An update draws what the fresh data displays, so a layer the data no longer carries leaves the plot."""

    @staticmethod
    def _drawing_both(fake_dpg: _FakeDPG) -> GUIWaveformGraph:
        """A graph showing the original and the reconstruction, each with its series on the axis."""
        graph = _graph()
        graph.current_data = TestWaveformDataUpdateRefit._waveform_data()
        graph.layers = {"Original": _Layer("Original"), "Reconstruction": _Layer("Reconstruction")}
        fake_dpg.set_children(
            "axis",
            [graph._series_tag("Original"), graph._series_tag("Reconstruction"), "indicator", "overlay"],
        )
        return graph

    def test_a_layer_the_data_no_longer_displays_leaves_with_its_series(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = self._drawing_both(fake_dpg)
        original_series = fake_dpg.alias_to_id[graph._series_tag("Original")]
        monkeypatch.setattr(graph, "_display_layers", lambda *_args, **_kwargs: [_Layer("Reconstruction")])

        graph.update_waveform_data(TestWaveformDataUpdateRefit._waveform_data())

        assert (list(graph.layers), fake_dpg.deleted) == (["Reconstruction"], [original_series])

    def test_layers_the_data_still_displays_stay(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = self._drawing_both(fake_dpg)
        monkeypatch.setattr(
            graph,
            "_display_layers",
            lambda *_args, **_kwargs: [_Layer("Original"), _Layer("Reconstruction")],
        )

        graph.update_waveform_data(TestWaveformDataUpdateRefit._waveform_data())

        assert (list(graph.layers), fake_dpg.deleted) == (["Original", "Reconstruction"], [])

    def test_a_layer_joining_the_plot_is_drawn_in_the_layers_order(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The series already drawn is taken off and added back behind the one that joins, as ordered."""
        graph = _graph()
        graph.current_data = TestWaveformDataUpdateRefit._waveform_data()
        graph.layers = {"Reconstruction": _Layer("Reconstruction")}
        fake_dpg.set_children("axis", [graph._series_tag("Reconstruction"), "indicator", "overlay"])
        added: List[str] = []
        monkeypatch.setattr(waveform_module.dpg, "add_line_series", lambda *args, **kwargs: added.append(kwargs["tag"]))
        monkeypatch.setattr(
            graph,
            "_display_layers",
            lambda *_args, **_kwargs: [_Layer("Reconstruction"), _Layer("Original")],
        )

        graph.update_waveform_data(TestWaveformDataUpdateRefit._waveform_data())

        assert added == [graph._series_tag("Reconstruction"), graph._series_tag("Original")]


class TestWaveformReconstructionDim:
    def test_series_color_is_untouched_when_not_dimmed(self) -> None:
        graph = _graph()
        layer = _Layer("Reconstruction")

        assert graph._series_color(layer, graph._series_shade(layer)) == layer.color

    def test_series_color_grays_the_reconstruction_when_dimmed(self) -> None:
        graph = _graph()
        _with_layout(graph, opacity=0.4)
        graph._reconstruction_dimmed = True

        layer = _Layer("Reconstruction")
        faded = graph._series_color(layer, graph._series_shade(layer))

        gray = round(0.299 * 255 + 0.587 * 200 + 0.114 * 100)
        assert faded.rgba == (gray, gray, gray, round(0.4 * 255))

    def test_series_color_leaves_other_layers_opaque_when_dimmed(self) -> None:
        graph = _graph()
        _with_layout(graph)
        graph._reconstruction_dimmed = True
        layer = _Layer("Sample Name")

        assert graph._series_color(layer, graph._series_shade(layer)) == layer.color

    def test_set_dimmed_rebinds_the_reconstruction_series_once(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = _graph()
        _with_layout(graph)
        graph.layers = {"Reconstruction": _Layer("Reconstruction")}
        series_tag = graph._series_tag("Reconstruction")
        fake_dpg.set_children("axis", [series_tag])
        binds: List[str] = []
        monkeypatch.setattr(
            waveform_module,
            "dpg_bind_item_theme",
            lambda tag, theme: binds.append(theme),
        )

        graph.set_reconstruction_dimmed(True)
        assert graph._reconstruction_dimmed is True
        assert len(binds) == 1

        graph.set_reconstruction_dimmed(True)
        assert len(binds) == 1

    def test_set_dimmed_without_reconstruction_layer_is_a_noop(self) -> None:
        graph = _graph()

        graph.set_reconstruction_dimmed(True)

        assert graph._reconstruction_dimmed is True

    def test_set_dimmed_shows_then_clears_the_status_message(self) -> None:
        graph = _graph()

        graph.set_reconstruction_dimmed(True)
        graph._status_bar.set.assert_called_with("Regenerating reconstruction...")

        graph.set_reconstruction_dimmed(False)
        graph._status_bar.set.assert_called_with("")

    def test_new_data_keeps_the_reconstruction_dimmed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An edit landing while later ones are still on their way redraws the waveform still faded."""
        graph = _graph()
        graph.set_reconstruction_dimmed(True)
        monkeypatch.setattr(graph, "clear_layers", MagicMock())
        monkeypatch.setattr(graph, "_restate_clock_ticks", MagicMock())
        monkeypatch.setattr(graph, "_display_layers", MagicMock(return_value=[]))
        graph._x_range = (0.0, 1.0)
        waveform_data = WaveformData(
            original_audio=None,
            approximation=np.zeros(4),
            approximations={},
            coefficient=1.0,
            frame_length=1,
            sample_rate=4,
        )

        graph.load_waveform_data(waveform_data)

        assert graph._reconstruction_dimmed is True


class TestAClickReportsASampleOfDrawnAudio:
    """The graph reports the sample a click named while it draws the audio its player sounds."""

    @staticmethod
    def _graph_reporting_clicks(monkeypatch: pytest.MonkeyPatch) -> Tuple[GUIWaveformGraph, List[int]]:
        graph = _graph()
        graph.current_data = MagicMock()
        graph._plays_what_it_draws = True
        graph._default_x_range = (0.0, 1.0)
        graph._default_y_range = (-1.0, 1.0)
        graph._layout = SimpleNamespace(waveform=SimpleNamespace(max_display_points=VOICE_SAMPLES))
        monkeypatch.setattr(graph, "add_layer", lambda _layer: None)
        monkeypatch.setattr(graph, "_update_display", lambda: None)
        clicked: List[int] = []
        graph.on_position_clicked = clicked.append
        return graph, clicked

    def test_a_click_reports_the_nearest_sample(self, monkeypatch: pytest.MonkeyPatch) -> None:
        graph, clicked = self._graph_reporting_clicks(monkeypatch)

        graph._on_plot_clicked(420.6)

        assert clicked == [421]

    def test_a_voice_drawn_in_place_of_the_audio_takes_no_click(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A hand-written voice's waveform is none of the audio the tab's player sounds."""
        graph, clicked = self._graph_reporting_clicks(monkeypatch)

        graph.load_voice_waveform(
            np.zeros(VOICE_SAMPLES, dtype=np.float32),
            name="voice",
            color=LiteralColor((255, 255, 255, 255)),
        )
        graph._on_plot_clicked(420.6)

        assert clicked == []

    def test_a_graph_emptied_takes_no_click(self, monkeypatch: pytest.MonkeyPatch) -> None:
        graph, clicked = self._graph_reporting_clicks(monkeypatch)

        graph.clear_layers()
        graph._on_plot_clicked(420.6)

        assert clicked == []


class TestClearingKeepsThePositionIndicator:
    def test_the_indicator_is_drawn_again_after_the_axis_is_emptied(
        self,
        fake_dpg: _FakeDPG,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        graph = _graph()
        graph.current_position = 900
        graph.indicator_theme = MagicMock()
        graph.overlay_theme = MagicMock()
        _with_layout(graph)
        graph._layout.graph = SimpleNamespace(min_y=-1.0, max_y=1.0)  # type: ignore[attr-defined]
        indicators: List[Dict[str, Any]] = []
        monkeypatch.setattr(waveform_module, "dpg_delete_children", lambda tag: fake_dpg.set_children(tag, []))
        monkeypatch.setattr(waveform_module.dpg, "add_inf_line_series", lambda x, **kwargs: indicators.append(kwargs))
        monkeypatch.setattr(waveform_module.dpg, "add_shade_series", lambda *args, **kwargs: None)
        monkeypatch.setattr(graph, "clear_layers", lambda: None)

        graph.clear()

        assert [indicator["tag"] for indicator in indicators] == [graph.position_indicator_tag]
        assert indicators[0]["show"] is False
        assert graph.current_position == 0
