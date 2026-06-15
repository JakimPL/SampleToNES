from unittest.mock import patch

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells, active_label


@pytest.mark.parametrize(
    "pending, width, expected",
    [
        ("", 3, "___"),
        ("0", 3, "0__"),
        ("05", 3, "05_"),
        ("", 1, "_"),
        ("F", 1, "F"),
    ],
)
def test_active_label_pads_with_underscores(pending: str, width: int, expected: str) -> None:
    assert active_label(pending, width) == expected


def _render(key: str) -> str:
    return f"label-{key}"


class TestEditableCells:
    def test_reset_seeds_values_and_clears_widgets(self) -> None:
        cells: EditableCells[str] = EditableCells()
        cells.register("a", 1)

        cells.reset({"a": "x"})

        assert cells.widget("a") is None
        assert cells.values == {"a": "x"}

    def test_reconcile_updates_only_changed_registered_cells(self) -> None:
        cells: EditableCells[str] = EditableCells()
        cells.reset({"a": "x", "b": "y"})
        cells.register("a", 10)
        cells.register("b", 20)

        with patch("dearpygui.dearpygui.configure_item") as configure:
            cells.reconcile({"a": "x", "b": "z"}, render=_render)

        configure.assert_called_once_with(20, label="label-b")
        assert cells.values["b"] == "z"

    def test_reconcile_caches_value_even_without_a_widget(self) -> None:
        cells: EditableCells[str] = EditableCells()
        cells.reset({"a": "x"})

        with patch("dearpygui.dearpygui.configure_item") as configure:
            cells.reconcile({"a": "z"}, render=_render)

        configure.assert_not_called()
        assert cells.values["a"] == "z"
