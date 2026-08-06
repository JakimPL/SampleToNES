from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from sampletones_application.ui.elements.graphs import waveform as waveform_module
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph
from sampletones_application.utils.palette.color import PaletteColor


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

    def delete_item(self, item_id: int) -> None:
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
        waveform_module.dpg, "configure_item", lambda *args, **kwargs: instance.configured.append(args[0])
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
        self.color = PaletteColor(value=(255, 255, 255, 255))


class _Array:
    size = 1

    def tolist(self) -> List[float]:
        return [0.0]


def _graph() -> GUIWaveformGraph:
    graph = GUIWaveformGraph.__new__(GUIWaveformGraph)
    graph.y_axis_tag = "axis"
    graph.position_indicator_tag = "indicator"
    graph.overlay_rectangle_tag = "overlay"
    graph.layers = {}
    graph._reconstruction_dimmed = False
    graph._lbl_waveform_reconstruction = "Reconstruction"
    graph._status_bar = MagicMock()
    graph._msg_regenerating = "Regenerating reconstruction..."
    return graph


def _with_layout(graph: GUIWaveformGraph, opacity: float = 0.4) -> None:
    graph._layout = SimpleNamespace(  # type: ignore[assignment]
        colors=SimpleNamespace(waveform_reconstruction=PaletteColor(value=(255, 200, 100, 255))),
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


class TestWaveformReconstructionDim:
    def test_series_color_is_untouched_when_not_dimmed(self) -> None:
        graph = _graph()
        layer = _Layer("Reconstruction")

        assert graph._series_color(layer) == layer.color.rgba

    def test_series_color_greys_the_reconstruction_when_dimmed(self) -> None:
        graph = _graph()
        _with_layout(graph, opacity=0.4)
        graph._reconstruction_dimmed = True

        faded = graph._series_color(_Layer("Reconstruction"))

        gray = round(0.299 * 255 + 0.587 * 200 + 0.114 * 100)
        assert faded == (gray, gray, gray, round(0.4 * 255))

    def test_series_color_leaves_other_layers_opaque_when_dimmed(self) -> None:
        graph = _graph()
        _with_layout(graph)
        graph._reconstruction_dimmed = True
        layer = _Layer("Sample Name")

        assert graph._series_color(layer) == layer.color.rgba

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
        monkeypatch.setattr(waveform_module, "dpg_bind_item_theme", lambda tag, theme: binds.append(theme))

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
