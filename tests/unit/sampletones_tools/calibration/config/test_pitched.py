from sampletones_tools.calibration.config.pitched import PitchedConfig


class TestPitchedConfig:
    def test_the_packaged_sounds_read(self) -> None:
        assert PitchedConfig.load().decaying.frequencies
