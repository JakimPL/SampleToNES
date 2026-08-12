from unittest.mock import patch

import pytest

from sampletones_application.ui.elements.table.cells import EditableCells, pending_label


@pytest.mark.parametrize(
    "pending, stored, width, expected",
    [
        ("", "AB", 3, "AB"),  # navigating onto a populated cell keeps its value
        ("", "...", 3, "..."),  # an empty cell stays empty (no underscore)
        ("0", "AB", 3, "0.."),  # typing shows the entered digits, padded with dots
        ("05", "AB", 3, "05."),
        ("058", "AB", 3, "058"),  # full width: just the typed digits
        ("", "F", 1, "F"),
        ("F", "x", 1, "F"),
    ],
)
def test_pending_label_preserves_value_until_typing(pending: str, stored: str, width: int, expected: str) -> None:
    assert pending_label(pending, stored, width) == expected


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

    def test_a_registered_widget_reads_back_as_its_key(self) -> None:
        """A cell cache answers from both sides, because a handler reports the widget it fired for."""
        cells: EditableCells[str] = EditableCells()
        cells.register("a", 1)

        assert cells.key(1) == "a"
        assert cells.widget("a") == 1

    def test_a_rebuild_drops_both_directions(self) -> None:
        cells: EditableCells[str] = EditableCells()
        cells.register("a", 1)
        cells.reset({})

        assert cells.key(1) is None
        assert cells.widget("a") is None

    def test_an_unknown_widget_names_no_cell(self) -> None:
        cells: EditableCells[str] = EditableCells()

        assert cells.key(1) is None

    def test_reconcile_caches_value_even_without_a_widget(self) -> None:
        cells: EditableCells[str] = EditableCells()
        cells.reset({"a": "x"})

        with patch("dearpygui.dearpygui.configure_item") as configure:
            cells.reconcile({"a": "z"}, render=_render)

        configure.assert_not_called()
        assert cells.values["a"] == "z"
