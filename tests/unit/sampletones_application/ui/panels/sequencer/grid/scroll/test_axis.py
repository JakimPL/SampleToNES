from typing import List

import pytest

from sampletones_application.ui.panels.sequencer.grid.scroll.axis import (
    HorizontalScroll,
    VerticalScroll,
)

AXIS_MODULE = "sampletones_application.ui.panels.sequencer.grid.scroll.axis.dpg"
POINTER = [12.0, 34.0]
SCROLL = 7.0
SCROLL_MAX = 70.0
ISSUED = 5.0


def _read_pointer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(f"{AXIS_MODULE}.get_mouse_pos", lambda local: POINTER)


class TestVerticalScroll:
    """A table whose rows run down the screen travels by height."""

    def test_the_pointer_reads_as_its_height(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _read_pointer(monkeypatch)

        assert VerticalScroll(table="tracker.table").pointer() == POINTER[1]

    def test_the_offsets_are_the_table_s_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        issued: List[float] = []
        monkeypatch.setattr(f"{AXIS_MODULE}.get_y_scroll", lambda table: SCROLL)
        monkeypatch.setattr(f"{AXIS_MODULE}.get_y_scroll_max", lambda table: SCROLL_MAX)
        monkeypatch.setattr(f"{AXIS_MODULE}.set_y_scroll", lambda table, offset: issued.append(offset))
        axis = VerticalScroll(table="tracker.table")

        axis.set_scroll(ISSUED)

        assert axis.scroll() == SCROLL
        assert axis.scroll_max() == SCROLL_MAX
        assert issued == [ISSUED]


class TestHorizontalScroll:
    """A table whose columns run across the screen travels by width."""

    def test_the_pointer_reads_as_its_width(self, monkeypatch: pytest.MonkeyPatch) -> None:
        _read_pointer(monkeypatch)

        assert HorizontalScroll(table="order.table").pointer() == POINTER[0]

    def test_the_offsets_are_the_table_s_own(self, monkeypatch: pytest.MonkeyPatch) -> None:
        issued: List[float] = []
        monkeypatch.setattr(f"{AXIS_MODULE}.get_x_scroll", lambda table: SCROLL)
        monkeypatch.setattr(f"{AXIS_MODULE}.get_x_scroll_max", lambda table: SCROLL_MAX)
        monkeypatch.setattr(f"{AXIS_MODULE}.set_x_scroll", lambda table, offset: issued.append(offset))
        axis = HorizontalScroll(table="order.table")

        axis.set_scroll(ISSUED)

        assert axis.scroll() == SCROLL
        assert axis.scroll_max() == SCROLL_MAX
        assert issued == [ISSUED]
