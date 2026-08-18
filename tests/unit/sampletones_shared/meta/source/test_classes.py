from typing import Final, List

from sampletones_shared.meta.source.classes import declared_subclasses
from tests.suite.source import parse_source

CLASSES_SOURCE: Final[str] = """
from package import AbstractElement
import package


class DialogElements(AbstractElement):
    OK = "ok"


class QualifiedElements(package.AbstractElement):
    EXIT = "exit"


class MixedElements(Mixin, AbstractElement):
    HELP = "help"


class Panel(StrEnum):
    MENU = "menu"


class Holder:
    class NestedElements(AbstractElement):
        INNER = "inner"


def build() -> None:
    class LocalElements(AbstractElement):
        LOCAL = "local"
"""

ELEMENT_BASE: Final[str] = "AbstractElement"


def names(source: str, base: str) -> List[str]:
    return declared_subclasses(parse_source(source), base)


class TestDeclaredSubclasses:
    def test_a_class_over_the_base_is_read(self) -> None:
        assert "DialogElements" in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_a_base_written_as_an_attribute_chain_is_read(self) -> None:
        assert "QualifiedElements" in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_a_base_beside_another_is_read(self) -> None:
        assert "MixedElements" in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_a_class_over_another_base_stays_aside(self) -> None:
        assert "Panel" not in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_a_class_nested_in_another_is_read(self) -> None:
        assert "NestedElements" in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_a_class_declared_inside_a_function_is_read(self) -> None:
        assert "LocalElements" in names(CLASSES_SOURCE, ELEMENT_BASE)

    def test_classes_are_read_outermost_first(self) -> None:
        assert names(CLASSES_SOURCE, ELEMENT_BASE) == [
            "DialogElements",
            "QualifiedElements",
            "MixedElements",
            "NestedElements",
            "LocalElements",
        ]

    def test_a_base_nothing_derives_from_is_read_from_nowhere(self) -> None:
        assert names(CLASSES_SOURCE, "AbsentBase") == []
