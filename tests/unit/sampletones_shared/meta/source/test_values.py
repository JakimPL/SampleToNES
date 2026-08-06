import ast
from dataclasses import dataclass
from typing import Dict, Final, Mapping, Tuple

import pytest

from sampletones_shared.meta.source.bindings.environment import TypeEnvironment
from sampletones_shared.meta.source.values import UNRESOLVED, EnumTable, ResolvedValues, ValueResolver
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase

ENUMS: Final[EnumTable] = {
    "Page": {"GLOBAL": "global"},
    "Panel": {"DIALOG": "dialog"},
    "TextType": {"LABEL": "label"},
    "DialogElements": {"OK": "ok", "CANCEL": "cancel"},
    "MenuElements": {"GROUP_FILE": "group_file", "ITEM_EXIT": "item_exit"},
}

ENVIRONMENT: Final[TypeEnvironment] = TypeEnvironment(
    types={
        "element": "DialogElements",
        "self._element": "MenuElements",
        "path": "Path",
    }
)


def expression(text: str) -> ast.expr:
    return ast.parse(text, mode="eval").body


CONSTANTS: Final[Mapping[str, ast.expr]] = {
    "OK_KEY": expression("'global.dialog.label.ok'"),
    "CHAINED_KEY": expression("OK_KEY"),
    "CYCLE": expression("CYCLE"),
    "BUILT": expression("build('global')"),
}

RESOLVER: Final[ValueResolver] = ValueResolver(environment=ENVIRONMENT, enums=ENUMS, constants=CONSTANTS)


class TestResolveValues(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        expression: str
        expected: Tuple[Tuple[str, ...], bool]

    test_cases = [
        TestCase(
            label="string_literal",
            expression="'global.dialog.label.ok'",
            expected=(("global.dialog.label.ok",), True),
        ),
        TestCase(label="enum_member", expression="Page.GLOBAL", expected=(("global",), True)),
        TestCase(
            label="enum_typed_name",
            expression="element",
            expected=(("ok", "cancel"), False),
        ),
        TestCase(
            label="enum_typed_attribute",
            expression="self._element",
            expected=(("group_file", "item_exit"), False),
        ),
        TestCase(
            label="enum_call",
            expression="MenuElements(entry.action.value)",
            expected=(("group_file", "item_exit"), False),
        ),
        TestCase(
            label="conditional_over_members",
            expression="DialogElements.OK if is_confirmation else DialogElements.CANCEL",
            expected=(("ok", "cancel"), True),
        ),
        TestCase(
            label="conditional_mixing_a_member_and_a_name",
            expression="DialogElements.OK if is_confirmation else element",
            expected=(("ok", "cancel"), False),
        ),
        TestCase(
            label="constant_holding_a_key",
            expression="OK_KEY",
            expected=(("global.dialog.label.ok",), True),
        ),
        TestCase(
            label="constant_naming_another_constant",
            expression="CHAINED_KEY",
            expected=(("global.dialog.label.ok",), True),
        ),
        TestCase(label="member_absent_from_its_enum", expression="Page.MISSING", expected=((), False)),
        TestCase(label="attribute_of_another_type", expression="settings.value", expected=((), False)),
        TestCase(label="call_of_another_kind", expression="str(key)", expected=((), False)),
        TestCase(label="format_string", expression="f'global.dialog.label.{name}'", expected=((), False)),
        TestCase(label="number", expression="4", expected=((), False)),
        TestCase(label="name_of_another_type", expression="path", expected=((), False)),
        TestCase(label="name_the_source_never_states", expression="unknown", expected=((), False)),
        TestCase(label="constant_naming_itself", expression="CYCLE", expected=((), False)),
        TestCase(label="constant_built_by_a_call", expression="BUILT", expected=((), False)),
        TestCase(
            label="conditional_reaching_an_unknown_branch",
            expression="DialogElements.OK if is_confirmation else unknown",
            expected=((), False),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_resolve(self, test_case: TestCase) -> None:
        resolved = RESOLVER.resolve(expression(test_case.expression))
        assert (resolved.values, resolved.exact) == test_case.expected


class TestResolvedValues:
    def test_values_mark_a_resolution(self) -> None:
        assert ResolvedValues(values=("ok",), exact=True).resolved

    def test_an_empty_resolution_reaches_nothing(self) -> None:
        assert not UNRESOLVED.resolved


class TestValueResolverTables:
    def test_an_enum_absent_from_the_table_resolves_nothing(self) -> None:
        resolver = ValueResolver(environment=ENVIRONMENT, enums={}, constants={})
        assert resolver.resolve(expression("Page.GLOBAL")) == UNRESOLVED

    def test_an_enum_holding_no_member_resolves_nothing(self) -> None:
        enums: Dict[str, Dict[str, str]] = {"AbstractElement": {}}
        environment = TypeEnvironment(types={"element": "AbstractElement"})
        resolver = ValueResolver(environment=environment, enums=enums, constants={})
        assert resolver.resolve(expression("element")) == UNRESOLVED
