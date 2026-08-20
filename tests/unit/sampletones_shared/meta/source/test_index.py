import ast
from pathlib import Path
from typing import Final

from sampletones_shared.meta.source.index import SourceIndex, source_index
from sampletones_shared.meta.source.modules import SourceModule
from tests.suite.source import parse_source

TAGS_SOURCE: Final[str] = """
from typing import Dict, Final

FILTERS: Final[Dict[ExportFormat, FileFilterElements]] = {}
TAG_MAIN_WINDOW = "main.window"
"""

PANEL_SOURCE: Final[str] = """
from typing import Dict, Final

LABELS: Final[Dict[str, MenuElements]] = {}
TAG_MAIN_WINDOW = "panel.window"
"""


def module(name: str, source: str) -> SourceModule:
    return SourceModule(path=Path(name), tree=parse_source(source))


def index_of(*sources: str) -> SourceIndex:
    return source_index([module(f"module_{number}.py", source) for number, source in enumerate(sources)])


class TestSourceIndex:
    def test_a_container_states_its_item_types(self) -> None:
        assert index_of(TAGS_SOURCE).item_types["FILTERS"] == (
            "ExportFormat",
            "FileFilterElements",
        )

    def test_a_constant_states_its_value(self) -> None:
        value = index_of(TAGS_SOURCE).constants["TAG_MAIN_WINDOW"]
        assert ast.unparse(value) == "'main.window'"

    def test_every_module_of_the_tree_is_read(self) -> None:
        index = index_of(TAGS_SOURCE, PANEL_SOURCE)
        assert {"FILTERS", "LABELS"}.issubset(index.item_types)

    def test_the_module_read_last_states_a_shared_spelling(self) -> None:
        index = index_of(TAGS_SOURCE, PANEL_SOURCE)
        assert ast.unparse(index.constants["TAG_MAIN_WINDOW"]) == "'panel.window'"

    def test_a_tree_of_no_modules_states_nothing(self) -> None:
        index = source_index([])
        assert (index.item_types, index.constants) == ({}, {})
