from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Tuple

import pytest

from sampletones_application.ui.elements import menu_section as menu_section_module
from sampletones_application.ui.elements.menu_section import MenuSection

MENU_TAG = "menu"
MARKER_TAG = "menu_marker"


class _DearPyGuiRecorder:
    """Stands in for the framework, recording what a section states and takes away."""

    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []
        self.built: List[str] = []
        self.containers: List[str] = []
        self.deleted: List[int] = []
        self.bound: List[Tuple[str, str]] = []

    def add_group(self, *, tag: str) -> int:
        self.built.append(f"group:{tag}")
        return 0

    @contextmanager
    def item_handler_registry(self, **_kwargs: Any) -> Iterator[int]:
        yield 0

    def add_item_visible_handler(self, **_kwargs: Any) -> int:
        return 0

    def bind_item_handler_registry(self, item: str, registry: str) -> None:
        self.bound.append((item, registry))

    def append_items(self, tag: str, build: Callable[[], None]) -> Tuple[int, ...]:
        self.containers.append(tag)
        standing = len(self.items)
        build()
        return tuple(range(standing, len(self.items)))

    def add_item(self) -> int:
        self.items.append({})
        return 0

    def delete_item(self, item: int) -> None:
        self.deleted.append(item)


@pytest.fixture
def framework(monkeypatch: pytest.MonkeyPatch) -> _DearPyGuiRecorder:
    instance = _DearPyGuiRecorder()
    monkeypatch.setattr(menu_section_module.dpg, "add_group", instance.add_group)
    monkeypatch.setattr(menu_section_module.dpg, "item_handler_registry", instance.item_handler_registry)
    monkeypatch.setattr(menu_section_module.dpg, "add_item_visible_handler", instance.add_item_visible_handler)
    monkeypatch.setattr(menu_section_module.dpg, "bind_item_handler_registry", instance.bind_item_handler_registry)
    monkeypatch.setattr(menu_section_module, "dpg_append_items", instance.append_items)
    monkeypatch.setattr(menu_section_module, "dpg_delete_item", instance.delete_item)
    return instance


def _section(
    build: Callable[[], None],
    *,
    menu_tag: str = MENU_TAG,
) -> MenuSection:
    return MenuSection(menu_tag=menu_tag, marker_tag=MARKER_TAG, build=build)


class TestSectionPlacement:
    def test_the_items_are_stated_into_the_menu_itself(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        """A section belongs to one menu, so its items land in that menu and nowhere else."""
        _section(framework.add_item).refresh()

        assert framework.containers == [MENU_TAG]

    def test_the_marker_is_what_the_section_is_reported_by(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        section = _section(framework.add_item)
        section.add_marker()
        section.watch()

        assert framework.built[0] == f"group:{MARKER_TAG}"
        assert [item for item, _ in framework.bound] == [MARKER_TAG]

    def test_a_build_takes_away_only_what_the_one_before_it_stated(
        self,
        framework: _DearPyGuiRecorder,
    ) -> None:
        """The menu's own items stand where they are, since only the last build is taken away."""
        section = _section(framework.add_item)

        section.refresh()
        section.refresh()

        assert framework.deleted == [0]


class TestSectionRefresh:
    """DearPyGui reports the marker drawn once a frame while the menu stands open, so a gap in
    those reports is what marks a fresh opening."""

    def test_the_items_are_stated_once_while_the_menu_stays_open(
        self,
        framework: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        frames = iter([10, 11, 12, 13])
        monkeypatch.setattr(menu_section_module.dpg, "get_frame_count", lambda: next(frames))
        requests: List[int] = []
        section = _section(lambda: requests.append(1))

        for _ in range(4):
            section._on_marker_drawn(0, 0)

        assert len(requests) == 1

    def test_the_items_are_stated_afresh_each_time_the_menu_is_opened(
        self,
        framework: _DearPyGuiRecorder,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        frames = iter([10, 11, 40, 41])
        monkeypatch.setattr(menu_section_module.dpg, "get_frame_count", lambda: next(frames))
        requests: List[int] = []
        section = _section(lambda: requests.append(1))

        for _ in range(4):
            section._on_marker_drawn(0, 0)

        assert len(requests) == 2
