from pathlib import Path

from sampletones_application.config.profile import UserProfile
from sampletones_application.paths import APPLICATION_STATE_PATH
from sampletones_shared.paths.user import APPLICATION_CONFIG_PATH


class TestUserProfile:
    """The profile a normal run reads, which is the one place naming the shipped locations."""

    def test_the_user_profile_names_the_shipped_locations(self) -> None:
        profile = UserProfile.user()

        assert profile.config == APPLICATION_CONFIG_PATH
        assert profile.state == APPLICATION_STATE_PATH

    def test_a_profile_keeps_the_locations_it_was_given(self, tmp_path: Path) -> None:
        """A run pointed elsewhere reads and writes there, which is what isolates one from another."""
        profile = UserProfile(
            config=tmp_path / "config.yaml",
            state=tmp_path / "state.yaml",
        )

        assert profile.config == tmp_path / "config.yaml"
        assert profile.state == tmp_path / "state.yaml"
