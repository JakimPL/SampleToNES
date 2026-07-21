from pathlib import Path

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.session import SessionManager


class TestSessionManagerInit:
    def test_instantiation_succeeds(self) -> None:
        session = SessionManager()
        assert session is not None


class TestSessionManagerWindowProperties:
    def test_fullscreen_property_returns_bool(self) -> None:
        session = SessionManager()
        assert isinstance(session.fullscreen, bool)

    def test_window_coordinate_properties_return_ints(self) -> None:
        session = SessionManager()
        assert isinstance(session.window_x, int)
        assert isinstance(session.window_y, int)
        assert isinstance(session.window_width, int)
        assert isinstance(session.window_height, int)

    def test_set_window_state_fullscreen_updates_fullscreen(self) -> None:
        session = SessionManager()
        session.set_window_state(True, 0, 0, 0, 0)
        assert session.fullscreen is True

    def test_set_window_state_non_fullscreen_updates_dimensions(self) -> None:
        session = SessionManager()
        session.set_window_state(False, 10, 20, 800, 600)
        assert session.window_x == 10
        assert session.window_y == 20
        assert session.window_width == 800
        assert session.window_height == 600


class TestSessionManagerTabAndSettings:
    def test_current_tab_property_returns_string(self) -> None:
        session = SessionManager()
        assert isinstance(session.current_tab, str)

    def test_set_current_tab_updates_current_tab(self) -> None:
        session = SessionManager()
        session.set_current_tab(Tab.INSTRUCTIONS)
        assert session.current_tab == Tab.INSTRUCTIONS

    def test_toggle_show_advanced_settings_returns_bool(self) -> None:
        session = SessionManager()
        result = session.toggle_show_advanced_settings()
        assert isinstance(result, bool)

    def test_advanced_settings_property_reflects_toggle(self) -> None:
        session = SessionManager()
        initial = session.advanced_settings
        session.toggle_show_advanced_settings()
        assert session.advanced_settings != initial

    def test_toggle_autoplay_returns_bool(self) -> None:
        session = SessionManager()
        result = session.toggle_autoplay()
        assert isinstance(result, bool)

    def test_autoplay_property_reflects_toggle(self) -> None:
        session = SessionManager()
        initial = session.autoplay
        session.toggle_autoplay()
        assert session.autoplay != initial


class TestSessionManagerCurrentState:
    def test_current_project_is_none_by_default_or_path(self) -> None:
        session = SessionManager()
        assert session.current_project is None or isinstance(
            session.current_project,
            Path,
        )

    def test_set_current_reconstruction_updates_property(self, tmp_path: Path) -> None:
        session = SessionManager()
        path = tmp_path / "rec.json"
        session.set_current_reconstruction(path)
        assert session.current_reconstruction == path

    def test_set_current_project_updates_property(self, tmp_path: Path) -> None:
        session = SessionManager()
        path = tmp_path / "project.stp"
        session.set_current_project(path)
        assert session.current_project == path


class TestSessionManagerPaths:
    def test_set_and_get_config_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_config_path(tmp_path / "config.json")
        result = session.get_config_path()
        assert isinstance(result, Path)

    def test_set_and_get_library_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_library_path(tmp_path / "lib.nlib")
        result = session.get_library_path()
        assert isinstance(result, Path)

    def test_set_and_get_instrument_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_instrument_path(tmp_path / "instr.json")
        result = session.get_instrument_path()
        assert isinstance(result, Path)

    def test_set_and_get_reconstruction_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_reconstruction_path(tmp_path / "rec.json")
        result = session.get_reconstruction_path()
        assert isinstance(result, Path)

    def test_set_and_get_audio_input_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_audio_input_path(tmp_path / "clip.wav")
        result = session.get_audio_input_path()
        assert isinstance(result, Path)

    def test_set_and_get_audio_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_audio_path(tmp_path / "audio.wav")
        result = session.get_audio_path()
        assert isinstance(result, Path)

    def test_set_and_get_project_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        session.set_project_path(tmp_path / "project.stp")
        result = session.get_project_path()
        assert isinstance(result, Path)


class TestSessionManagerFavorites:
    def test_toggle_favorite_adds_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        path = tmp_path / "favorite"
        session.toggle_favorite(path)
        assert path in session.favorites

    def test_toggle_favorite_twice_removes_path(self, tmp_path: Path) -> None:
        session = SessionManager()
        path = tmp_path / "favorite"
        session.toggle_favorite(path)
        session.toggle_favorite(path)
        assert path not in session.favorites

    def test_favorites_returns_set(self) -> None:
        session = SessionManager()
        assert isinstance(session.favorites, set)
