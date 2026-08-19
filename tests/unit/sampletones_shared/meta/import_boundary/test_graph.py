from typing import Final

from sampletones_shared.meta.import_boundary.graph import LayerGraph

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
