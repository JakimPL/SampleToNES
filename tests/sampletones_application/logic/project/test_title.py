from dataclasses import dataclass

from sampletones_application.logic.project.title import document_title, is_any_unsaved


@dataclass
class State:
    name: str
    unsaved_changes: bool


UNTITLED = "Untitled"


class TestDocumentTitle:
    def test_project_is_primary(self) -> None:
        project, reconstruction = State("Song", False), State("Recon", False)
        assert document_title(project, reconstruction, untitled=UNTITLED, reconstruction_loaded=False) == "Song"

    def test_unsaved_project_is_marked(self) -> None:
        project, reconstruction = State("Song", True), State("", False)
        assert document_title(project, reconstruction, untitled=UNTITLED, reconstruction_loaded=False) == "Song*"

    def test_untitled_fallback(self) -> None:
        project, reconstruction = State("", False), State("", False)
        assert document_title(project, reconstruction, untitled=UNTITLED, reconstruction_loaded=False) == "Untitled"

    def test_reconstruction_appended_as_secondary(self) -> None:
        project, reconstruction = State("Song", False), State("Recon", True)
        title = document_title(project, reconstruction, untitled=UNTITLED, reconstruction_loaded=True)
        assert title == "Song — Recon*"


class TestIsAnyUnsaved:
    def test_either_unsaved(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", True)) is True
        assert is_any_unsaved(State("a", True), State("b", False)) is True

    def test_both_clean(self) -> None:
        assert is_any_unsaved(State("a", False), State("b", False)) is False
