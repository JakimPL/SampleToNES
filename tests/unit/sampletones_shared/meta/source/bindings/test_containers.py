import ast
from typing import Dict, Final, List, Optional, Tuple

from sampletones_shared.meta.source.bindings.containers import (
    container_item_types,
    iterated_container,
    iterated_types,
)
from tests.suite.source import parse_source

FILTER_TYPES: Final[Tuple[str, ...]] = ("ExportFormat", "FileFilterElements")

ANNOTATED_SOURCE: Final[str] = """
from typing import Dict, Final, List

FILTERS: Final[Dict[ExportFormat, FileFilterElements]] = {}
NAMES: Final[List[str]] = []
PLAIN = {}


class Panel:
    def _load(self) -> None:
        self._labels: Dict[MenuElements, str] = {}
"""


def expression(source: str) -> ast.expr:
    return ast.parse(source, mode="eval").body


def loop_target(source: str) -> ast.expr:
    statement = parse_source(source).body[0]
    assert isinstance(statement, ast.For)
    return statement.target


def typed_names(
    target: str,
    accessor: Optional[str],
    item_types: Tuple[str, ...],
) -> List[Tuple[str, str]]:
    types = iterated_types(
        loop_target(f"for {target} in container: pass"),
        accessor,
        item_types,
    )
    return [(ast.unparse(entry.target), entry.type_name) for entry in types]


class TestIteratedContainer:
    def test_a_mapping_walked_directly_is_read(self) -> None:
        container = iterated_container(expression("FILTERS"))
        assert container is not None and (container.spelling, container.accessor) == (
            "FILTERS",
            None,
        )

    def test_an_accessor_travels_with_the_container(self) -> None:
        container = iterated_container(expression("self._filters.items()"))
        assert container is not None and (container.spelling, container.accessor) == (
            "self._filters",
            "items",
        )

    def test_a_call_of_another_kind_reads_no_container(self) -> None:
        assert iterated_container(expression("enumerate(FILTERS)")) is None

    def test_a_computed_iterable_reads_no_container(self) -> None:
        assert iterated_container(expression("first + second")) is None


class TestIteratedTypes:
    def test_walking_items_types_the_key_and_the_value_target(self) -> None:
        assert typed_names("export_format, element", "items", FILTER_TYPES) == [
            ("export_format", "ExportFormat"),
            ("element", "FileFilterElements"),
        ]

    def test_walking_items_onto_one_target_types_nothing(self) -> None:
        assert typed_names("pair", "items", FILTER_TYPES) == []

    def test_walking_values_types_the_target_from_the_value_type(self) -> None:
        assert typed_names("element", "values", FILTER_TYPES) == [
            (
                "element",
                "FileFilterElements",
            )
        ]

    def test_walking_keys_types_the_target_from_the_key_type(self) -> None:
        assert typed_names("export_format", "keys", FILTER_TYPES) == [
            (
                "export_format",
                "ExportFormat",
            )
        ]

    def test_walking_a_container_directly_types_the_target_from_the_key_type(
        self,
    ) -> None:
        assert typed_names("export_format", None, FILTER_TYPES) == [
            (
                "export_format",
                "ExportFormat",
            )
        ]

    def test_walking_a_sequence_types_the_target_from_its_item_type(self) -> None:
        assert typed_names("name", None, ("str",)) == [("name", "str")]

    def test_a_container_stating_no_item_types_types_nothing(self) -> None:
        assert typed_names("name", None, ()) == []


class TestContainerItemTypes:
    def test_an_annotated_mapping_states_its_key_and_value_types(self) -> None:
        assert container_item_types(parse_source(ANNOTATED_SOURCE))["FILTERS"] == FILTER_TYPES

    def test_an_annotated_sequence_states_its_item_type(self) -> None:
        assert container_item_types(parse_source(ANNOTATED_SOURCE))["NAMES"] == ("str",)

    def test_a_container_without_an_annotation_stays_aside(self) -> None:
        assert "PLAIN" not in container_item_types(parse_source(ANNOTATED_SOURCE))

    def test_a_container_annotated_inside_a_method_is_read(self) -> None:
        item_types: Dict[str, Tuple[str, ...]] = container_item_types(parse_source(ANNOTATED_SOURCE))
        assert item_types["self._labels"] == ("MenuElements", "str")
