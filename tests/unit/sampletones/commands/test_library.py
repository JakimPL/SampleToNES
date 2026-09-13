from pathlib import Path
from typing import List

import pytest

from sampletones.commands.registry import COMMANDS
from sampletones.dispatcher import dispatch
from sampletones_core.configs import Config

GENERATOR = "sampletones_core.headless.library.generate_library"
LOADER = "sampletones_core.headless.config.load_config"


class TestLibrary:
    def test_the_library_is_generated_for_the_configuration_named(self, monkeypatch: pytest.MonkeyPatch) -> None:
        generated: List[Config] = []
        loaded: List[Path] = []
        configuration = Config()

        def load_config(path: Path) -> Config:
            loaded.append(path)
            return configuration

        monkeypatch.setattr(GENERATOR, generated.append)
        monkeypatch.setattr(LOADER, load_config)

        assert dispatch(COMMANDS, ["library", "--config", "custom.json"]) == 0
        assert loaded == [Path("custom.json")]
        assert generated == [configuration]
