from sampletones_application.logic.project.session import ProjectSession


class TestProjectSession:
    def test_initial_state(self) -> None:
        session = ProjectSession()
        assert session.name == ""
        assert session.unsaved_changes is False

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
        calls: list[int] = []
        session.on_state_changed = lambda: calls.append(1)
        session.mark_updated()
        session.mark_saved()
        assert calls == [1, 1]
