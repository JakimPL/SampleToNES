from typing import Final, List

from sampletones_shared.meta.source.bindings.scopes import module_scopes
from sampletones_shared.meta.source.subscripts import SubscriptSite, find_subscripts
from tests.suite.source import parse_source, scope_named

RECEIVER_TYPE: Final[str] = "LanguageManager"

PANEL_SOURCE: Final[str] = """
class Panel:
    def __init__(self, language_manager: LanguageManager) -> None:
        self._language_manager = language_manager
        self._title = language_manager["global.dialog.title.main"]
        self._message = language_manager["global.dialog.message.main"]

    def _label(self, element: MenuElements) -> str:
        return self._language_manager[Page.GLOBAL, Panel.MENU, TextType.LABEL, element]

    def _load(self, language_manager: LanguageManager) -> None:
        def label(element: MenuElements) -> str:
            return language_manager[Page.GLOBAL, Panel.MENU, TextType.LABEL, element]

        self._labels = [label(item) for item in items]

    def _stored(self, mapping: Dict[str, str]) -> str:
        return mapping["key"]
"""


def sites_of(name: str) -> List[SubscriptSite]:
    scopes = module_scopes(parse_source(PANEL_SOURCE), imported_item_types={})
    scope = scope_named(scopes, name)
    return find_subscripts(scope.node, scope.environment.spellings_of(RECEIVER_TYPE))


class TestFindSubscripts:
    def test_a_lookup_on_a_parameter_is_found(self) -> None:
        assert [site.receiver for site in sites_of("__init__")] == [
            "language_manager",
            "language_manager",
        ]

    def test_a_lookup_on_an_attribute_is_found(self) -> None:
        assert [site.receiver for site in sites_of("_label")] == ["self._language_manager"]

    def test_a_lookup_inside_a_nested_function_belongs_to_that_function(self) -> None:
        assert sites_of("_load") == []

    def test_a_nested_function_holds_its_own_lookup(self) -> None:
        assert [site.receiver for site in sites_of("label")] == ["language_manager"]

    def test_a_subscript_on_another_type_stays_aside(self) -> None:
        assert sites_of("_stored") == []

    def test_sites_arrive_in_source_order(self) -> None:
        assert [site.line for site in sites_of("__init__")] == [5, 6]

    def test_a_string_key_holds_one_part(self) -> None:
        first, _ = sites_of("__init__")
        assert len(first.parts) == 1

    def test_a_tuple_key_holds_a_part_for_each_member(self) -> None:
        (site,) = sites_of("_label")
        assert len(site.parts) == 4
