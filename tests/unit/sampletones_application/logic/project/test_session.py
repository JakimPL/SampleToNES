from typing import List

from sampletones_application.logic.project.session import ProjectSession


class TestProjectSession:
    def test_initial_state(self) -> None:
        session = ProjectSession()
        assert session.name == ""
        assert session.unsaved_changes is False
        assert session.is_open is False

    def test_mark_updated_then_saved(self) -> None:
        session = ProjectSession()
        session.mark_updated()
        assert session.unsaved_changes is True
        session.mark_saved("song")
        assert session.unsaved_changes is False
        assert session.name == "song"

    def test_mark_loaded_then_closed(self) -> None:
        session = ProjectSession()
        session.mark_loaded("demo")
        assert session.name == "demo"
        assert session.unsaved_changes is False
        session.mark_updated()
        session.mark_closed()
        assert session.name == ""
        assert session.unsaved_changes is False

    def test_state_change_callback(self) -> None:
        session = ProjectSession()
        calls: List[int] = []
        session.on_state_changed = lambda: calls.append(1)
        session.mark_updated()
        session.mark_saved()
        assert calls == [1, 1]

    def test_is_open_after_mark_loaded(self) -> None:
        session = ProjectSession()
        session.mark_loaded("demo")
        assert session.is_open is True

    def test_is_open_after_mark_loaded_empty_name(self) -> None:
        session = ProjectSession()
        session.mark_loaded("")
        assert session.is_open is True

    def test_is_open_false_after_mark_closed(self) -> None:
        session = ProjectSession()
        session.mark_loaded("demo")
        session.mark_closed()
        assert session.is_open is False

    def test_is_open_unchanged_by_mark_updated(self) -> None:
        session = ProjectSession()
        session.mark_loaded("demo")
        session.mark_updated()
        assert session.is_open is True

    def test_is_open_unchanged_by_mark_saved(self) -> None:
        session = ProjectSession()
        session.mark_loaded("demo")
        session.mark_saved("demo2")
        assert session.is_open is True
