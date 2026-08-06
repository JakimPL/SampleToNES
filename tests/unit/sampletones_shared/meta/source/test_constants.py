import ast
from typing import Dict, Final, List

from sampletones_shared.meta.source.constants import ModuleConstant, module_constants
from tests.suite.source import parse_source

CONSTANTS_SOURCE: Final[str] = """
from typing import Dict, Final

TAG_MAIN_WINDOW = "main.window"
SUF_BUTTON: Final[str] = "button"
FIRST = SECOND = "shared"
TAG_TUPLE, TAG_OTHER = ("first", "second")
FILTERS: Final[Dict[str, str]] = {"module": "ftm"}
DECLARED: Final[str]
holder.attribute = "outside"


def build() -> str:
    inner = "local"
    return inner
"""


def by_name(source: str) -> Dict[str, ModuleConstant]:
    return {constant.name: constant for constant in module_constants(parse_source(source))}


def names(source: str) -> List[str]:
    return [constant.name for constant in module_constants(parse_source(source))]


class TestModuleConstants:
    def test_a_plain_assignment_is_read(self) -> None:
        assert "TAG_MAIN_WINDOW" in names(CONSTANTS_SOURCE)

    def test_an_annotated_assignment_is_read(self) -> None:
        assert "SUF_BUTTON" in names(CONSTANTS_SOURCE)

    def test_a_chained_assignment_yields_every_name(self) -> None:
        assert {"FIRST", "SECOND"}.issubset(names(CONSTANTS_SOURCE))

    def test_a_tuple_target_binds_no_plain_name(self) -> None:
        assert {"TAG_TUPLE", "TAG_OTHER"}.isdisjoint(names(CONSTANTS_SOURCE))

    def test_an_annotation_alone_binds_nothing(self) -> None:
        assert "DECLARED" not in names(CONSTANTS_SOURCE)

    def test_an_attribute_target_binds_no_plain_name(self) -> None:
        assert "attribute" not in names(CONSTANTS_SOURCE)

    def test_a_local_assignment_stays_in_its_function(self) -> None:
        assert "inner" not in names(CONSTANTS_SOURCE)

    def test_the_value_travels_with_the_name(self) -> None:
        constant = by_name(CONSTANTS_SOURCE)["TAG_MAIN_WINDOW"]
        assert ast.unparse(constant.value) == "'main.window'"

    def test_a_chained_assignment_shares_one_value(self) -> None:
        constants = by_name(CONSTANTS_SOURCE)
        assert constants["FIRST"].value is constants["SECOND"].value

    def test_an_annotation_travels_with_the_name(self) -> None:
        constant = by_name(CONSTANTS_SOURCE)["FILTERS"]
        assert constant.annotation is not None and ast.unparse(constant.annotation) == "Final[Dict[str, str]]"

    def test_a_plain_assignment_states_no_annotation(self) -> None:
        assert by_name(CONSTANTS_SOURCE)["TAG_MAIN_WINDOW"].annotation is None

    def test_the_line_names_where_the_statement_sits(self) -> None:
        assert by_name(CONSTANTS_SOURCE)["TAG_MAIN_WINDOW"].line == 4

    def test_constants_are_read_in_source_order(self) -> None:
        assert names(CONSTANTS_SOURCE) == ["TAG_MAIN_WINDOW", "SUF_BUTTON", "FIRST", "SECOND", "FILTERS"]
