from dataclasses import dataclass

from sampletones_application.logic.project.title.unsaved import is_any_unsaved


@dataclass
class State:
    name: str
    unsaved_changes: bool


class TestIsAnyUnsaved:
    def test_either_unsaved(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", True)) is True
        assert is_any_unsaved(State("a", True), State("b", False)) is True

    def test_both_clean(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", False)) is False
