from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Tuple

import pytest

from sampletones_application.tags.compose import TAG_SEPARATOR, compose_tag
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.errors import expect_error


class _Layer(StrEnum):
    PULSE_ONE = "pulse_1"


class TestComposeTag(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        parts: Tuple[Any, ...]

    test_cases = (
        TestCase(
            label="single_part",
            parts=("plot",),
            expected="plot",
        ),
        TestCase(
            label="two_parts",
            parts=("handler", "mouse"),
            expected="handler.mouse",
        ),
        TestCase(
            label="four_parts",
            parts=("a", "b", "c", "d"),
            expected="a.b.c.d",
        ),
        TestCase(
            label="uppercase_lowers",
            parts=("Pulse", "Duty"),
            expected="pulse.duty",
        ),
        TestCase(
            label="space_becomes_underscore",
            parts=("my layer",),
            expected="my_layer",
        ),
        TestCase(
            label="whitespace_run_collapses",
            parts=("my   layer",),
            expected="my_layer",
        ),
        TestCase(
            label="surrounding_whitespace_strips",
            parts=("  layer  ",),
            expected="layer",
        ),
        TestCase(label="tab_and_newline_normalize", parts=("a\tb\nc",), expected="a_b_c"),
        TestCase(
            label="composed_base_contributes_its_segments",
            parts=("global.graph.y_axis", "theme"),
            expected="global.graph.y_axis.theme",
        ),
        TestCase(
            label="str_enum_member_serves_as_part",
            parts=(_Layer.PULSE_ONE, "graph"),
            expected="pulse_1.graph",
        ),
        TestCase(
            label="digits_survive",
            parts=("layer", "12"),
            expected="layer.12",
        ),
        TestCase(
            label="no_part_raises",
            parts=(),
            expected=ValueError,
        ),
        TestCase(
            label="empty_part_raises",
            parts=("base", ""),
            expected=ValueError,
        ),
        TestCase(
            label="whitespace_only_part_raises",
            parts=("base", "   "),
            expected=ValueError,
        ),
    )

    @pytest.mark.parametrize(
        "test_case",
        test_cases,
        ids=lambda test_case: test_case.label,
    )
    def test_compose_tag(self, test_case: TestCase) -> None:
        if not expect_error(compose_tag, test_case.expected, *test_case.parts):
            assert compose_tag(*test_case.parts) == test_case.expected


class TestComposeTagInvariants:
    def test_composition_is_associative(self) -> None:
        """Building a tag in one call matches extending an already-composed parent."""
        parent = compose_tag("global", "graph")
        assert compose_tag(parent, "theme") == compose_tag("global", "graph", "theme")

    def test_every_segment_is_separated(self) -> None:
        composed = compose_tag("a", "b", "c")
        assert composed.count(TAG_SEPARATOR) == 2

    def test_casing_and_spacing_of_a_runtime_name_do_not_change_the_tag(self) -> None:
        assert compose_tag("base", "My Layer") == compose_tag("base", "my_layer")
