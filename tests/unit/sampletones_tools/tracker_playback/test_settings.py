from sampletones_tools.tracker_playback.settings import PlaybackSettings


class TestPlaybackSettings:
    def test_the_shipped_settings_load_from_the_package(self) -> None:
        assert PlaybackSettings.load().examples_per_difference >= 1
