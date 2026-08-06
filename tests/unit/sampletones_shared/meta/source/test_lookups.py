from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Mapping, Tuple

import pytest

from sampletones_shared.meta.source.index import source_index
from sampletones_shared.meta.source.lookups import LookupSite, composed_values, module_lookups, tree_lookups
from sampletones_shared.meta.source.modules import SourceModule
from sampletones_shared.meta.source.values import UNRESOLVED, EnumTable, ResolvedValues
from tests.suite.base import BaseTestSuite
from tests.suite.case import BaseRegularTestCase
from tests.suite.source import parse_source

SEPARATOR: Final[str] = "."
RECEIVER_TYPE: Final[str] = "LanguageManager"

ENUMS: Final[EnumTable] = {
    "Page": {"GLOBAL": "global", "MAIN": "main"},
    "Panel": {"DIALOG": "dialog"},
    "TextType": {"LABEL": "label"},
    "DialogElements": {"OK": "ok", "EXIT": "exit"},
    "AbstractElement": {},
}

PANEL_SOURCE: Final[str] = """
class Panel:
    def __init__(self, language_manager: LanguageManager) -> None:
        self._language_manager = language_manager
        self._title = language_manager["global.dialog.label.ok"]

    def _label(self, element: DialogElements) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]

    def _literal_label(self) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, DialogElements.EXIT]

    def _wide_label(self, element: AbstractElement) -> str:
        return self._language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element]

    def _built_label(self, name: str) -> str:
        return self._language_manager[f"global.dialog.label.{name}"]

    def _stored(self, mapping: Dict[str, str]) -> str:
        return mapping["global.dialog.label.ok"]
"""

CONSTANT_SOURCE: Final[str] = """
DEFAULT_KEY = "global.dialog.label.ok"


def label(language_manager: LanguageManager) -> str:
    return language_manager[DEFAULT_KEY]
"""


def module(name: str, source: str) -> SourceModule:
    return SourceModule(path=Path(name), tree=parse_source(source))


def lookups(*sources: str) -> List[LookupSite]:
    modules = [module(f"module_{number}.py", source) for number, source in enumerate(sources)]
    return tree_lookups(
        modules,
        index=source_index(modules),
        enums=ENUMS,
        receiver_type=RECEIVER_TYPE,
        separator=SEPARATOR,
    )


def site_on_line(source: str, line: int) -> LookupSite:
    single = module("panel.py", source)
    found = module_lookups(
        single,
        index=source_index([single]),
        enums=ENUMS,
        receiver_type=RECEIVER_TYPE,
        separator=SEPARATOR,
    )
    for site in found:
        if site.location == f"panel.py:{line}":
            return site

    raise AssertionError(f"no lookup sits on line {line}")


class TestComposedValues(BaseTestSuite):
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseRegularTestCase):
        resolutions: Tuple[ResolvedValues, ...]
        expected: Tuple[str, ...]

    literal_global = ResolvedValues(values=("global",), exact=True)
    literal_dialog = ResolvedValues(values=("dialog",), exact=True)
    literal_label = ResolvedValues(values=("label",), exact=True)

    test_cases = [
        TestCase(
            label="one_part",
            resolutions=(ResolvedValues(values=("global.dialog.label.ok",), exact=True),),
            expected=("global.dialog.label.ok",),
        ),
        TestCase(
            label="four_parts",
            resolutions=(
                literal_global,
                literal_dialog,
                literal_label,
                ResolvedValues(values=("ok",), exact=True),
            ),
            expected=("global.dialog.label.ok",),
        ),
        TestCase(
            label="one_part_reaching_two_values",
            resolutions=(
                literal_global,
                literal_dialog,
                literal_label,
                ResolvedValues(values=("ok", "exit"), exact=False),
            ),
            expected=("global.dialog.label.ok", "global.dialog.label.exit"),
        ),
        TestCase(
            label="two_parts_reaching_two_values_each",
            resolutions=(
                ResolvedValues(values=("global", "main"), exact=False),
                literal_dialog,
                literal_label,
                ResolvedValues(values=("ok", "exit"), exact=False),
            ),
            expected=(
                "global.dialog.label.ok",
                "global.dialog.label.exit",
                "main.dialog.label.ok",
                "main.dialog.label.exit",
            ),
        ),
        TestCase(
            label="a_part_out_of_reach",
            resolutions=(literal_global, literal_dialog, literal_label, UNRESOLVED),
            expected=(),
        ),
        TestCase(
            label="no_parts",
            resolutions=(),
            expected=("",),
        ),
    ]

    @pytest.mark.parametrize("test_case", test_cases, ids=lambda test_case: test_case.label)
    def test_composed_values(self, test_case: "TestComposedValues.TestCase") -> None:
        assert composed_values(test_case.resolutions, SEPARATOR) == test_case.expected


class TestModuleLookups:
    def test_a_literal_value_states_itself(self) -> None:
        site = site_on_line(PANEL_SOURCE, 5)
        assert (site.values, site.exact) == (("global.dialog.label.ok",), True)

    def test_parts_of_literal_members_state_one_value(self) -> None:
        site = site_on_line(PANEL_SOURCE, 11)
        assert (site.values, site.exact) == (("global.dialog.label.exit",), True)

    def test_a_part_arriving_in_a_variable_states_every_member(self) -> None:
        site = site_on_line(PANEL_SOURCE, 8)
        assert set(site.values) == {"global.dialog.label.ok", "global.dialog.label.exit"}

    def test_a_value_reached_through_an_enum_is_no_literal(self) -> None:
        assert site_on_line(PANEL_SOURCE, 8).exact is False

    def test_a_part_typed_by_an_enum_without_members_reaches_nothing(self) -> None:
        site = site_on_line(PANEL_SOURCE, 14)
        assert (site.values, site.unresolved_parts, site.resolved) == ((), ("'element'",), False)

    def test_a_value_an_f_string_builds_reaches_nothing(self) -> None:
        site = site_on_line(PANEL_SOURCE, 17)
        assert site.values == ()
        assert "f'global.dialog.label." in site.unresolved_parts[0]

    def test_a_subscript_on_another_type_is_no_lookup(self) -> None:
        assert [site for site in lookups(PANEL_SOURCE) if site.location.endswith(":20")] == []

    def test_every_lookup_of_the_module_is_read(self) -> None:
        assert len(lookups(PANEL_SOURCE)) == 5

    def test_a_receiver_the_module_never_states_leaves_it_aside(self) -> None:
        assert lookups("def label(mapping: Dict[str, str]) -> str:\n    return mapping['key']") == []


class TestTreeLookups:
    def test_a_constant_declared_in_another_module_states_its_value(self) -> None:
        declaring = 'DEFAULT_KEY = "global.dialog.label.ok"\n'
        reading = "def label(language_manager: LanguageManager) -> str:\n    return language_manager[DEFAULT_KEY]\n"
        (site,) = lookups(declaring, reading)
        assert (site.values, site.exact) == (("global.dialog.label.ok",), True)

    def test_a_constant_declared_in_the_same_module_states_its_value(self) -> None:
        (site,) = lookups(CONSTANT_SOURCE)
        assert site.values == ("global.dialog.label.ok",)

    def test_a_container_annotated_in_another_module_types_a_walked_target(self) -> None:
        declaring = "from typing import Dict, Final\n\nFILTERS: Final[Dict[str, DialogElements]] = {}\n"
        reading = (
            "def labels(language_manager: LanguageManager) -> None:\n"
            "    for element in FILTERS.values():\n"
            "        print(language_manager[Page.GLOBAL, Panel.DIALOG, TextType.LABEL, element])\n"
        )
        (site,) = lookups(declaring, reading)
        assert set(site.values) == {"global.dialog.label.ok", "global.dialog.label.exit"}

    def test_every_module_of_the_tree_is_read(self) -> None:
        first = "def label(language_manager: LanguageManager) -> str:\n    return language_manager['global.dialog.label.ok']"
        second = "def title(language_manager: LanguageManager) -> str:\n    return language_manager['global.dialog.label.exit']"
        locations: Mapping[str, str] = {site.location: site.values[0] for site in lookups(first, second)}
        assert locations == {
            "module_0.py:2": "global.dialog.label.ok",
            "module_1.py:2": "global.dialog.label.exit",
        }

    def test_a_tree_of_no_modules_states_no_lookups(self) -> None:
        assert lookups() == []
