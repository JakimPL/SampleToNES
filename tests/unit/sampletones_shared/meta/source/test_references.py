from typing import Dict, Final

from sampletones_shared.meta.source.references import count_identifier_loads
from tests.suite.source import parse_source

REFERENCES_SOURCE: Final[str] = """
from sampletones_application.tags.general import SUF_BUTTON, SUF_UNUSED

SUF_BUTTON_COPY = compose_tag(SUF_BUTTON, "copy")
TAG_PANEL = "panel"
EXPORTED = ["SUF_UNUSED"]


def create(state) -> None:
    build(TAG_PANEL, SUF_BUTTON_COPY)
    state.reset()
    print(TAG_PANEL)
"""


def counts(source: str) -> Dict[str, int]:
    return count_identifier_loads(parse_source(source))


class TestCountIdentifierLoads:
    def test_a_read_name_is_counted(self) -> None:
        assert counts(REFERENCES_SOURCE)["SUF_BUTTON"] == 1

    def test_a_name_read_twice_counts_twice(self) -> None:
        assert counts(REFERENCES_SOURCE)["TAG_PANEL"] == 2

    def test_a_declaration_alone_counts_nothing(self) -> None:
        assert "EXPORTED" not in counts(REFERENCES_SOURCE)

    def test_an_import_alone_counts_nothing(self) -> None:
        assert "SUF_UNUSED" not in counts(REFERENCES_SOURCE)

    def test_a_constant_feeding_another_constant_counts_as_read(self) -> None:
        assert counts(REFERENCES_SOURCE)["SUF_BUTTON_COPY"] == 1

    def test_an_attribute_read_is_counted(self) -> None:
        assert counts(REFERENCES_SOURCE)["reset"] == 1

    def test_an_attribute_written_counts_nothing(self) -> None:
        assert "stored" not in counts("self.stored = value")

    def test_a_name_inside_a_string_counts_nothing(self) -> None:
        assert "TAG_PANEL" not in counts("label = 'TAG_PANEL'")
