from pathlib import Path

import pytest

from sampletones_application.categories.hierarchy import Tab
from sampletones_application.config.managers.session import SessionManager
from sampletones_application.config.profile import UserProfile
from sampletones_application.tags.sequencer import TAG_SEQUENCER_BROWSER_PANEL


@pytest.fixture
def session(tmp_path: Path) -> SessionManager:
    """A session over a profile of its own, in the state a first run finds."""
    return SessionManager(
        UserProfile(
            config=tmp_path / "config.yaml",
            state=tmp_path / "state.yaml",
        )
    )


class TestSessionManagerInit:
    def test_instantiation_succeeds(self, session: SessionManager) -> None:
        assert session is not None


class TestSessionManagerWindowProperties:
    def test_fullscreen_property_returns_bool(self, session: SessionManager) -> None:
        assert isinstance(session.fullscreen, bool)

    def test_window_coordinate_properties_return_ints(self, session: SessionManager) -> None:
        assert isinstance(session.window_x, int)
        assert isinstance(session.window_y, int)
        assert isinstance(session.window_width, int)
        assert isinstance(session.window_height, int)

    def test_set_window_state_fullscreen_updates_fullscreen(self, session: SessionManager) -> None:
        session.set_window_state(True, 0, 0, 0, 0)
        assert session.fullscreen is True

    def test_set_window_state_non_fullscreen_updates_dimensions(self, session: SessionManager) -> None:
        session.set_window_state(False, 10, 20, 800, 600)
        assert session.window_x == 10
        assert session.window_y == 20
        assert session.window_width == 800
        assert session.window_height == 600


class TestSessionManagerKeybindings:
    def test_shortcut_scheme_name_reflects_what_was_set(self, session: SessionManager) -> None:
        session.set_shortcut_scheme_name("compact")
        assert session.shortcut_scheme_name == "compact"

    def test_shortcut_overrides_reflect_what_was_set(self, session: SessionManager) -> None:
        session.set_shortcut_overrides({"Undo": "Ctrl+Alt+U"})
        assert session.shortcut_overrides == {"Undo": "Ctrl+Alt+U"}


class TestSessionManagerTabAndSettings:
    def test_current_tab_property_returns_string(self, session: SessionManager) -> None:
        assert isinstance(session.current_tab, str)

    def test_set_current_tab_updates_current_tab(self, session: SessionManager) -> None:
        session.set_current_tab(Tab.INSTRUCTIONS)
        assert session.current_tab == Tab.INSTRUCTIONS

    def test_toggle_show_advanced_settings_returns_bool(self, session: SessionManager) -> None:
        result = session.toggle_show_advanced_settings()
        assert isinstance(result, bool)

    def test_advanced_settings_property_reflects_toggle(self, session: SessionManager) -> None:
        initial = session.advanced_settings
        session.toggle_show_advanced_settings()
        assert session.advanced_settings != initial

    def test_toggle_autoplay_returns_bool(self, session: SessionManager) -> None:
        result = session.toggle_autoplay()
        assert isinstance(result, bool)

    def test_autoplay_property_reflects_toggle(self, session: SessionManager) -> None:
        initial = session.autoplay
        session.toggle_autoplay()
        assert session.autoplay != initial


class TestSessionManagerCurrentState:
    def test_a_fresh_session_holds_no_current_project(self, session: SessionManager) -> None:
        assert session.current_project is None

    def test_set_current_reconstruction_updates_property(
        self,
        session: SessionManager,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "rec.json"
        session.set_current_reconstruction(path)
        assert session.current_reconstruction == path

    def test_set_current_project_updates_property(
        self,
        session: SessionManager,
        tmp_path: Path,
    ) -> None:
        path = tmp_path / "project.stp"
        session.set_current_project(path)
        assert session.current_project == path


class TestSessionManagerPaths:
    def test_set_and_get_config_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_config_path(tmp_path / "config.json")
        assert isinstance(session.get_config_path(), Path)

    def test_set_and_get_library_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_library_path(tmp_path / "lib.nlib")
        assert isinstance(session.get_library_path(), Path)

    def test_set_and_get_instrument_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_instrument_path(tmp_path / "instr.json")
        assert isinstance(session.get_instrument_path(), Path)

    def test_set_and_get_reconstruction_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_reconstruction_path(tmp_path / "rec.json")
        assert isinstance(session.get_reconstruction_path(), Path)

    def test_set_and_get_audio_input_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_audio_input_path(tmp_path / "clip.wav")
        assert isinstance(session.get_audio_input_path(), Path)

    def test_set_and_get_audio_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_audio_path(tmp_path / "audio.wav")
        assert isinstance(session.get_audio_path(), Path)

    def test_set_and_get_project_path(self, session: SessionManager, tmp_path: Path) -> None:
        session.set_project_path(tmp_path / "project.stp")
        assert isinstance(session.get_project_path(), Path)


class TestSessionManagerFavorites:
    def test_toggle_favorite_adds_path(self, session: SessionManager, tmp_path: Path) -> None:
        path = tmp_path / "favorite"
        session.toggle_favorite(path)
        assert path in session.favorites

    def test_toggle_favorite_twice_removes_path(self, session: SessionManager, tmp_path: Path) -> None:
        path = tmp_path / "favorite"
        session.toggle_favorite(path)
        session.toggle_favorite(path)
        assert path not in session.favorites

    def test_favorites_returns_set(self, session: SessionManager) -> None:
        assert isinstance(session.favorites, set)

    def test_a_browser_reads_the_favorites_filter_it_was_given(self, session: SessionManager) -> None:
        session.set_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL, True)
        assert session.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL) is True

    def test_a_browser_a_first_run_finds_shows_the_whole_tree(self, session: SessionManager) -> None:
        assert session.is_favorites_filter_active(TAG_SEQUENCER_BROWSER_PANEL) is False
