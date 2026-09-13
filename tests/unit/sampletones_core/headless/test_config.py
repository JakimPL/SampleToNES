from pathlib import Path

from sampletones_core.configs import Config
from sampletones_core.headless.config import load_config


class TestLoadConfig:
    def test_a_file_named_is_read(self, tmp_path: Path) -> None:
        path = tmp_path / "config.json"
        path.write_text("{}", encoding="utf-8")

        assert load_config(path) == Config()

    def test_nothing_named_is_the_saved_configuration(self) -> None:
        assert load_config(None) == Config.default()
