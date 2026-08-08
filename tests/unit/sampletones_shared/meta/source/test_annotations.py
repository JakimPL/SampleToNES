import ast
from dataclasses import dataclass
from typing import Optional, Tuple

import pytest

from sampletones_shared.meta.source.annotations import (
    annotation_item_types,
    annotation_type_name,
    unwrap_annotation,
)
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase


def annotation(text: str) -> ast.expr:
    return ast.parse(text, mode="eval").body


class TestAnnotationTypeName(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        annotation: str
        expected: Optional[str]

    test_cases = (
        TestCase(label="plain_name", annotation="LanguageManager", expected="LanguageManager"),
        TestCase(
            label="optional",
            annotation="Optional[LanguageManager]",
            expected="LanguageManager",
        ),
        TestCase(
            label="final",
            annotation="Final[str]",
            expected="str",
        ),
        TestCase(
            label="class_variable",
            annotation="ClassVar[Page]",
            expected="Page",
        ),
        TestCase(
            label="annotated",
            annotation="Annotated[Page, 'unit']",
            expected="Page",
        ),
        TestCase(
            label="qualified_wrapper",
            annotation="typing.Optional[LanguageManager]",
            expected="LanguageManager",
        ),
        TestCase(
            label="qualified_name",
            annotation="categories.LanguageManager",
            expected="LanguageManager",
        ),
        TestCase(
            label="generic_states_itself",
            annotation="Dict[str, int]",
            expected="Dict",
        ),
        TestCase(
            label="wrapped_generic",
            annotation="Final[Dict[Page, Panel]]",
            expected="Dict",
        ),
        TestCase(
            label="nested_wrappers",
            annotation="Final[Optional[LanguageManager]]",
            expected="LanguageManager",
        ),
        TestCase(
            label="quoted",
            annotation="'LanguageManager'",
            expected="LanguageManager",
        ),
        TestCase(
            label="quoted_inside_wrapper",
            annotation="Optional['LanguageManager']",
            expected="LanguageManager",
        ),
        TestCase(
            label="none",
            annotation="None",
            expected=None,
        ),
        TestCase(
            label="call",
            annotation="build()",
            expected=None,
        ),
        TestCase(
            label="quoted_beyond_python",
            annotation="'not python('",
            expected=None,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_annotation_type_name(self, test_case: TestCase) -> None:
        assert annotation_type_name(annotation(test_case.annotation)) == test_case.expected

    def test_a_missing_annotation_names_nothing(self) -> None:
        assert annotation_type_name(None) is None


class TestAnnotationItemTypes(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        annotation: str
        expected: Tuple[str, ...]

    test_cases = (
        TestCase(
            label="mapping_states_key_then_value",
            annotation="Dict[TrackerFormat, FileFilterElements]",
            expected=("TrackerFormat", "FileFilterElements"),
        ),
        TestCase(
            label="wrapped_mapping",
            annotation="Final[Dict[TrackerFormat, FileFilterElements]]",
            expected=("TrackerFormat", "FileFilterElements"),
        ),
        TestCase(
            label="homogeneous_tuple",
            annotation="Tuple[MenuElements, ...]",
            expected=("MenuElements",),
        ),
        TestCase(
            label="list",
            annotation="List[MenuElements]",
            expected=("MenuElements",),
        ),
        TestCase(
            label="optional_item",
            annotation="List[Optional[MenuElements]]",
            expected=("MenuElements",),
        ),
        TestCase(
            label="nested_mapping",
            annotation="Dict[str, Dict[str, MenuElements]]",
            expected=("str", "Dict"),
        ),
        TestCase(
            label="plain_name_holds_nothing",
            annotation="str",
            expected=(),
        ),
        TestCase(
            label="unwrapped_scalar_holds_nothing",
            annotation="Optional[MenuElements]",
            expected=(),
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_annotation_item_types(self, test_case: TestCase) -> None:
        assert annotation_item_types(annotation(test_case.annotation)) == test_case.expected

    def test_a_missing_annotation_holds_nothing(self) -> None:
        assert annotation_item_types(None) == ()


class TestUnwrapAnnotation:
    def test_a_wrapper_gives_way_to_the_type_it_states(self) -> None:
        unwrapped = unwrap_annotation(annotation("Final[Optional[Page]]"))
        assert unwrapped is not None and ast.unparse(unwrapped) == "Page"

    def test_a_plain_annotation_stays_as_written(self) -> None:
        unwrapped = unwrap_annotation(annotation("Page"))
        assert unwrapped is not None and ast.unparse(unwrapped) == "Page"

    def test_a_generic_stays_as_written(self) -> None:
        unwrapped = unwrap_annotation(annotation("Dict[str, Page]"))
        assert unwrapped is not None and ast.unparse(unwrapped) == "Dict[str, Page]"

    def test_a_missing_annotation_unwraps_to_nothing(self) -> None:
        assert unwrap_annotation(None) is None
