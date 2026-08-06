import ast
from typing import Optional, Type

from sampletones_shared.meta.source.bindings.statements import (
    AliasStatement,
    LoopStatement,
    Statement,
    TypeStatement,
    read_statement,
)
from tests.suite.source import parse_source


def first_node(source: str, kind: Type[ast.AST]) -> ast.AST:
    return next(node for node in ast.walk(parse_source(source)) if isinstance(node, kind))


def statement_of(source: str, kind: Type[ast.AST]) -> Optional[Statement]:
    return read_statement(first_node(source, kind))


class TestAnnotations:
    def test_an_annotated_parameter_names_its_type(self) -> None:
        statement = statement_of("def label(element: MenuElements) -> str:\n    return ''", ast.arg)
        assert isinstance(statement, TypeStatement)
        assert (statement.spelling, statement.type_name) == ("element", "MenuElements")

    def test_a_parameter_without_an_annotation_states_nothing(self) -> None:
        assert statement_of("def label(element):\n    return ''", ast.arg) is None

    def test_an_annotated_attribute_names_its_type(self) -> None:
        statement = statement_of("self._manager: Optional[LanguageManager] = None", ast.AnnAssign)
        assert isinstance(statement, TypeStatement)
        assert (statement.spelling, statement.type_name) == ("self._manager", "LanguageManager")

    def test_an_annotation_alone_names_its_type(self) -> None:
        statement = statement_of("manager: LanguageManager", ast.AnnAssign)
        assert isinstance(statement, TypeStatement)
        assert (statement.spelling, statement.type_name) == ("manager", "LanguageManager")

    def test_an_annotated_subscript_states_nothing(self) -> None:
        assert statement_of("managers['first']: LanguageManager = build()", ast.AnnAssign) is None


class TestAssignments:
    def test_a_construction_names_the_type_it_builds(self) -> None:
        statement = statement_of("self._manager = LanguageManager(path)", ast.Assign)
        assert isinstance(statement, TypeStatement)
        assert (statement.spelling, statement.type_name) == ("self._manager", "LanguageManager")

    def test_a_construction_through_a_module_names_the_type(self) -> None:
        statement = statement_of("manager = categories.LanguageManager(path)", ast.Assign)
        assert isinstance(statement, TypeStatement)
        assert (statement.spelling, statement.type_name) == ("manager", "LanguageManager")

    def test_an_assignment_from_a_name_passes_that_name_along(self) -> None:
        statement = statement_of("self._manager = language_manager", ast.Assign)
        assert isinstance(statement, AliasStatement)
        assert (statement.target, statement.source) == ("self._manager", "language_manager")

    def test_an_assignment_from_an_attribute_passes_the_chain_along(self) -> None:
        statement = statement_of("self._same = self._manager", ast.Assign)
        assert isinstance(statement, AliasStatement)
        assert (statement.target, statement.source) == ("self._same", "self._manager")

    def test_an_assignment_from_a_literal_states_nothing(self) -> None:
        assert statement_of("TAG_MAIN = 'main'", ast.Assign) is None

    def test_a_chained_assignment_states_nothing(self) -> None:
        assert statement_of("first = second = build()", ast.Assign) is None

    def test_an_assignment_to_a_tuple_states_nothing(self) -> None:
        assert statement_of("first, second = pair", ast.Assign) is None


class TestLoops:
    def test_a_for_statement_binds_its_target_to_a_container(self) -> None:
        statement = statement_of("for element in FILTERS.values():\n    print(element)", ast.For)
        assert isinstance(statement, LoopStatement)
        assert (ast.unparse(statement.target), ast.unparse(statement.iterable)) == ("element", "FILTERS.values()")

    def test_a_comprehension_binds_its_target_to_a_container(self) -> None:
        statement = statement_of("labels = [label(item) for item in FILTERS]", ast.comprehension)
        assert isinstance(statement, LoopStatement)
        assert (ast.unparse(statement.target), ast.unparse(statement.iterable)) == ("item", "FILTERS")


class TestOtherNodes:
    def test_a_node_of_another_kind_states_nothing(self) -> None:
        assert statement_of("def label() -> str:\n    return ''", ast.Return) is None
