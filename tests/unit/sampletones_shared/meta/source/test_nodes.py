import ast
from typing import Final, Iterable, List

from sampletones_shared.meta.source.nodes import (
    expression_spelling,
    nested_scopes,
    own_nodes,
    slice_elements,
    terminal_name,
)
from tests.suite.source import parse_source

SCOPED_SOURCE: Final[str] = """
value = manager["module"]

class Holder:
    field: int = 1

    def method(self, key: str) -> str:
        return self._manager[key]

    def outer(self) -> None:
        def inner(element: str) -> None:
            print(element)
"""


def first_expression(source: str) -> ast.expr:
    statement = parse_source(source).body[0]
    assert isinstance(statement, ast.Expr)
    return statement.value


def first_subscript(source: str) -> ast.Subscript:
    expression = first_expression(source)
    assert isinstance(expression, ast.Subscript)
    return expression


def function_names(nodes: Iterable[ast.AST]) -> List[str]:
    return [node.name for node in nodes if isinstance(node, ast.FunctionDef)]


class TestSliceElements:
    def test_single_part_is_one_element(self) -> None:
        elements = slice_elements(first_subscript("manager['global.dialog.label.ok']"))
        assert len(elements) == 1

    def test_tuple_parts_are_split(self) -> None:
        elements = slice_elements(first_subscript("manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]"))
        assert [ast.unparse(element) for element in elements] == [
            "Page.GLOBAL",
            "Panel.DIALOG",
            "TextType.LABEL",
            "element",
        ]


class TestExpressionSpelling:
    def test_name_spells_itself(self) -> None:
        assert expression_spelling(first_expression("language_manager")) == "language_manager"

    def test_attribute_spells_the_chain(self) -> None:
        assert expression_spelling(first_expression("self._language_manager")) == "self._language_manager"

    def test_deep_attribute_spells_every_step(self) -> None:
        assert expression_spelling(first_expression("self._holder.manager")) == "self._holder.manager"

    def test_a_call_spells_nothing(self) -> None:
        assert expression_spelling(first_expression("build()")) is None

    def test_a_subscript_spells_nothing(self) -> None:
        assert expression_spelling(first_expression("managers['first']")) is None


class TestTerminalName:
    def test_name_is_its_own_terminal(self) -> None:
        assert terminal_name(first_expression("Optional")) == "Optional"

    def test_attribute_ends_at_its_last_step(self) -> None:
        assert terminal_name(first_expression("typing.Optional")) == "Optional"

    def test_a_call_ends_nowhere(self) -> None:
        assert terminal_name(first_expression("build()")) is None


class TestOwnNodes:
    def test_module_owns_its_top_level_statements(self) -> None:
        owned = list(own_nodes(parse_source(SCOPED_SOURCE)))
        assert any(isinstance(node, ast.Subscript) for node in owned)

    def test_module_owns_a_class_body(self) -> None:
        owned = list(own_nodes(parse_source(SCOPED_SOURCE)))
        assert any(isinstance(node, ast.AnnAssign) for node in owned)

    def test_module_leaves_function_parameters_to_their_function(self) -> None:
        owned = list(own_nodes(parse_source(SCOPED_SOURCE)))
        assert [node for node in owned if isinstance(node, ast.arg)] == []

    def test_a_function_owns_its_parameters(self) -> None:
        method = next(
            node for node in nested_scopes(parse_source(SCOPED_SOURCE)) if function_names([node]) == ["method"]
        )
        owned = list(own_nodes(method))
        assert [node.arg for node in owned if isinstance(node, ast.arg)] == ["self", "key"]

    def test_a_function_leaves_a_nested_function_aside(self) -> None:
        outer = next(node for node in nested_scopes(parse_source(SCOPED_SOURCE)) if function_names([node]) == ["outer"])
        assert function_names(own_nodes(outer)) == ["outer"]


class TestNestedScopes:
    def test_a_module_opens_the_methods_of_its_classes(self) -> None:
        assert function_names(nested_scopes(parse_source(SCOPED_SOURCE))) == ["method", "outer"]

    def test_a_function_opens_the_function_it_holds(self) -> None:
        outer = next(node for node in nested_scopes(parse_source(SCOPED_SOURCE)) if function_names([node]) == ["outer"])
        assert function_names(nested_scopes(outer)) == ["inner"]

    def test_a_lambda_opens_a_scope(self) -> None:
        tree = parse_source("labels = sorted(items, key=lambda item: item.name)")
        assert any(isinstance(node, ast.Lambda) for node in nested_scopes(tree))
