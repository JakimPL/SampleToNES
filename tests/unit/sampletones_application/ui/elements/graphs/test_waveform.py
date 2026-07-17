from typing import Any, Dict, List

import pytest

from sampletones_application.ui.elements.graphs import waveform as waveform_module
from sampletones_application.ui.elements.graphs.waveform import GUIWaveformGraph


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
        self.color = (255, 255, 255, 255)


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
    return graph


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
