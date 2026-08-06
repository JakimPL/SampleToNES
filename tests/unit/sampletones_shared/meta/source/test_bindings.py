import ast
from typing import Dict, Final, List, Mapping, Tuple

from sampletones_shared.meta.source.bindings import (
    Scope,
    TypeEnvironment,
    container_item_types,
    iterated_container,
    module_scopes,
)
from tests.suite.source import parse_source, scope_named

PANEL_SOURCE: Final[str] = """
from typing import Dict, Final

FILTERS: Final[Dict[TrackerFormat, FileFilterElements]] = {}


class Panel:
    def __init__(self, language_manager: LanguageManager, plain) -> None:
        self._language_manager = language_manager
        self._same_manager = self._language_manager
        self._built = LanguageManager(path)

    def _menu_label(self, element: MenuElements) -> str:
        return self._language_manager[element]

    def _context_label(self, element: ContextElements) -> str:
        return self._language_manager[element]

    def _load(self, language_manager: LanguageManager) -> None:
        def label(element: SequencerGridElements) -> str:
            return language_manager[element]

        self._labels = [label(item) for item in FILTERS.values()]

    def _filters(self) -> None:
        for tracker_format, element in FILTERS.items():
            print(tracker_format, element)

    def _names(self) -> None:
        for name in FILTERS:
            print(name)
"""

IMPORTED_SOURCE: Final[str] = """
def create() -> None:
    for tracker_format, element in TRACKER_FILTERS.items():
        print(tracker_format, element)
"""

LOCAL_OVER_IMPORTED_SOURCE: Final[str] = """
from typing import Dict, Final

TRACKER_FILTERS: Final[Dict[str, MenuElements]] = {}


def create() -> None:
    for element in TRACKER_FILTERS.values():
        print(element)
"""

IMPORTED_FILTERS: Final[Mapping[str, Tuple[str, ...]]] = {
    "TRACKER_FILTERS": ("TrackerFormat", "FileFilterElements"),
}


def read_scopes(source: str, imported_item_types: Mapping[str, Tuple[str, ...]]) -> List[Scope]:
    return module_scopes(parse_source(source), imported_item_types=imported_item_types)


def environment_of(source: str, name: str, imported_item_types: Mapping[str, Tuple[str, ...]]) -> TypeEnvironment:
    return scope_named(read_scopes(source, imported_item_types), name).environment


def panel_environment(name: str) -> TypeEnvironment:
    return environment_of(PANEL_SOURCE, name, {})


class TestParameterTypes:
    def test_a_parameter_annotation_states_its_type(self) -> None:
        assert panel_environment("_menu_label").type_of("element") == "MenuElements"

    def test_a_parameter_without_an_annotation_states_nothing(self) -> None:
        assert panel_environment("__init__").type_of("plain") is None

    def test_a_name_the_source_never_states_is_unknown(self) -> None:
        assert panel_environment("_menu_label").type_of("absent") is None


class TestScopeIsolation:
    def test_each_method_keeps_its_own_parameter_type(self) -> None:
        assert panel_environment("_context_label").type_of("element") == "ContextElements"

    def test_a_nested_parameter_stays_out_of_the_enclosing_scope(self) -> None:
        assert panel_environment("_load").type_of("element") is None

    def test_a_nested_scope_states_its_own_parameter(self) -> None:
        assert panel_environment("label").type_of("element") == "SequencerGridElements"

    def test_a_nested_scope_sees_the_enclosing_parameters(self) -> None:
        assert panel_environment("label").type_of("language_manager") == "LanguageManager"

    def test_the_module_scope_states_its_constants(self) -> None:
        module_scope = read_scopes(PANEL_SOURCE, {})[0]
        assert module_scope.environment.type_of("FILTERS") == "Dict"


class TestAttributeTypes:
    def test_an_assignment_carries_a_parameter_type_to_an_attribute(self) -> None:
        assert panel_environment("__init__").type_of("self._language_manager") == "LanguageManager"

    def test_an_attribute_type_reaches_every_method(self) -> None:
        assert panel_environment("_menu_label").type_of("self._language_manager") == "LanguageManager"

    def test_a_chain_of_assignments_carries_the_type_along(self) -> None:
        assert panel_environment("_menu_label").type_of("self._same_manager") == "LanguageManager"

    def test_a_direct_construction_states_its_type(self) -> None:
        assert panel_environment("_menu_label").type_of("self._built") == "LanguageManager"

    def test_the_spellings_of_a_type_name_every_holder(self) -> None:
        spellings = panel_environment("__init__").spellings_of("LanguageManager")
        assert set(spellings) == {
            "language_manager",
            "self._language_manager",
            "self._same_manager",
            "self._built",
        }

    def test_the_spellings_of_a_type_leave_other_names_aside(self) -> None:
        assert "element" not in panel_environment("_menu_label").spellings_of("LanguageManager")


class TestLoopTargets:
    def test_walking_items_states_the_key_and_the_value_type(self) -> None:
        environment = panel_environment("_filters")
        assert (environment.type_of("tracker_format"), environment.type_of("element")) == (
            "TrackerFormat",
            "FileFilterElements",
        )

    def test_walking_values_states_the_value_type(self) -> None:
        assert panel_environment("_load").type_of("item") == "FileFilterElements"

    def test_walking_a_mapping_states_the_key_type(self) -> None:
        assert panel_environment("_names").type_of("name") == "TrackerFormat"

    def test_an_imported_container_states_its_item_types(self) -> None:
        assert environment_of(IMPORTED_SOURCE, "create", IMPORTED_FILTERS).type_of("element") == "FileFilterElements"

    def test_a_container_the_module_annotates_states_its_own_item_types(self) -> None:
        environment = environment_of(LOCAL_OVER_IMPORTED_SOURCE, "create", IMPORTED_FILTERS)
        assert environment.type_of("element") == "MenuElements"


class TestIteratedContainer:
    def test_a_mapping_walked_directly_is_read(self) -> None:
        container = iterated_container(ast.parse("FILTERS", mode="eval").body)
        assert container is not None and (container.spelling, container.accessor) == ("FILTERS", None)

    def test_an_accessor_travels_with_the_container(self) -> None:
        container = iterated_container(ast.parse("self._filters.items()", mode="eval").body)
        assert container is not None and (container.spelling, container.accessor) == ("self._filters", "items")

    def test_a_call_of_another_kind_reads_no_container(self) -> None:
        assert iterated_container(ast.parse("enumerate(FILTERS)", mode="eval").body) is None


class TestContainerItemTypes:
    def test_an_annotated_container_states_its_item_types(self) -> None:
        item_types = container_item_types(parse_source(PANEL_SOURCE))
        assert item_types["FILTERS"] == ("TrackerFormat", "FileFilterElements")

    def test_a_container_annotated_inside_a_method_is_read(self) -> None:
        source = """
        from typing import Dict, Final

        class Panel:
            def _load(self) -> None:
                self._labels: Dict[MenuElements, str] = {}
        """
        item_types: Dict[str, Tuple[str, ...]] = container_item_types(parse_source(source))
        assert item_types["self._labels"] == ("MenuElements", "str")
