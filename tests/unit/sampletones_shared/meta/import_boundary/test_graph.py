from typing import Final

import pytest
from pydantic import ValidationError

from sampletones_shared.meta.import_boundary.graph import LayerGraph, reached_units

GRAPH: Final[LayerGraph] = LayerGraph(
    root="package",
    package="package",
    layers={"low": (), "high": ("low",), "high/nested": ("low",)},
)


class TestLayerRules:
    """A graph states what a unit may import, and the rule the check runs is what remains."""

    def test_one_rule_stands_for_each_declared_unit(self) -> None:
        assert len(GRAPH.rules()) == len(GRAPH.layers)

    def test_a_unit_forbids_the_units_its_layers_leave_out(self) -> None:
        low, _, _ = GRAPH.rules()
        assert low.forbidden == ("package.high", "package.high.nested")

    def test_a_unit_stays_free_of_the_units_it_may_import(self) -> None:
        _, high, _ = GRAPH.rules()
        assert "package.low" not in high.forbidden

    def test_a_unit_never_forbids_itself(self) -> None:
        assert all(rule.pattern.split("/")[0] not in rule.forbidden for rule in GRAPH.rules())

    def test_a_nested_unit_is_left_out_of_the_unit_around_it(self) -> None:
        _, high, _ = GRAPH.rules()
        assert high.excluding == ("high/nested/**/*.py",)

    def test_every_rule_is_written_against_the_graphs_root(self) -> None:
        assert all(rule.root == "package" for rule in GRAPH.rules())

    def test_a_rule_names_its_unit_by_the_glob_the_unit_holds(self) -> None:
        assert [rule.pattern for rule in GRAPH.rules()] == ["low/**/*.py", "high/**/*.py", "high/nested/**/*.py"]


class TestWellFormedGraphs:
    """A graph states an order over its units, so one it cannot state is refused as it is read."""

    def test_a_unit_reaching_an_undeclared_unit_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            LayerGraph(
                root="package",
                package="package",
                layers={"high": ("absent",)},
            )

    def test_a_graph_closing_a_cycle_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            LayerGraph(
                root="package",
                package="package",
                layers={"low": ("high",), "high": ("low",)},
            )

    def test_a_unit_importing_itself_is_refused(self) -> None:
        with pytest.raises(ValidationError):
            LayerGraph(
                root="package",
                package="package",
                layers={"low": ("low",)},
            )


class TestReachedUnits:
    """What a unit imports through the units it imports, which is what an order is read from."""

    def test_a_unit_reaches_what_its_layers_reach(self) -> None:
        assert reached_units(GRAPH.layers, "high") == {"low"}

    def test_a_unit_standing_on_nothing_reaches_nothing(self) -> None:
        assert reached_units(GRAPH.layers, "low") == set()
